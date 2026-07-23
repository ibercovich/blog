# frozen_string_literal: true

require "date"
require "json"
require "minitest/autorun"
require "pathname"
require "yaml"

class BooksCollectionTest < Minitest::Test
  ROOT = Pathname(__dir__).parent
  BOOK_PATHS = Dir[ROOT.join("_books/*.md")].sort.freeze
  STATUSES = %w[read want_to_read currently_reading tbd].freeze

  def books
    @books ||= BOOK_PATHS.map do |path|
      source = File.read(path, encoding: "UTF-8")
      match = source.match(/\A---\s*\n(.*?)\n---\s*\z/m)
      refute_nil match, "#{path} must contain only YAML front matter"
      YAML.safe_load(
        match[1],
        permitted_classes: [Date, Time],
        aliases: false
      ).merge("_path" => path)
    end
  end

  def test_books_are_individual_collection_records
    refute_empty books

    books.each do |book|
      path = book.fetch("_path")
      %w[title author color status].each do |field|
        refute_empty book[field].to_s, "#{path}: missing #{field}"
      end

      assert_match(/\A#[0-9A-Fa-f]{6}\z/, book.fetch("color"), "#{path}: invalid color")
      assert_includes STATUSES, book.fetch("status"), "#{path}: invalid status"
      assert_kind_of Array, book.fetch("collections", []), "#{path}: collections must be a list"

      %w[physical_copy recommended].each do |field|
        next unless book.key?(field)

        assert_includes [true, false], book[field], "#{path}: #{field} must be boolean"
      end

      isbn = book["isbn"].to_s
      unless isbn.empty?
        assert_match(/\A(?:\d{9}[\dX]|\d{13})\z/, isbn, "#{path}: invalid ISBN")
        assert valid_isbn?(isbn), "#{path}: invalid ISBN checksum"
      end

      next if book["cover"].to_s.empty?

      cover = ROOT.join(book.fetch("cover").delete_prefix("/"))
      assert cover.file?, "#{path}: missing cover #{cover}"
    end
  end

  def test_titles_and_isbns_are_unique
    assert_unique books.map { |book| book.fetch("title") }, "title"
    assert_unique books.map { |book| book["isbn"] }.compact, "ISBN"
  end

  def test_goodreads_import_is_complete_and_not_recommended
    imported = books.select { |book| book.key?("goodreads_id") }
    assert_equal 967, imported.length
    assert_unique imported.map { |book| book.fetch("goodreads_id").to_s }, "Goodreads ID"
    assert imported.all? { |book| book.fetch("goodreads_id").to_s.match?(/\A\d+\z/) }
    assert imported.none? { |book| book["recommended"] }, "imported books must not be recommended"
    assert_equal 89, books.count { |book| book["recommended"] == true }

    manifest_path = ROOT.join("_import/goodreads/library.jsonl")
    manifest = manifest_path.each_line.map do |line|
      JSON.parse(line) unless line.strip.empty?
    end.compact
    assert_equal 1_056, manifest.length
    assert_unique manifest.map { |row| row.fetch("goodreads_id") }, "manifest Goodreads ID"
    assert manifest.all? { |row| ROOT.join(row.fetch("record")).file? }
    assert_equal imported.map { |book| book.fetch("goodreads_id").to_s }.sort,
                 manifest.reject { |row| row.fetch("protected") }
                         .map { |row| row.fetch("goodreads_id") }
                         .sort
  end

  def test_books_page_is_only_a_shell
    page = ROOT.join("_pages/books.md").read
    refute_includes page, "window.__BOOKS"
    refute_includes page, '"synopsis"'
  end

  def test_interactive_shelf_uses_only_recommended_books
    layout = ROOT.join("_layouts/books.html").read
    assert_includes layout, "data.filter((book) => book.recommended === true)"
  end

  private

  def valid_isbn?(isbn)
    if isbn.length == 10
      return false unless isbn.match?(/\A\d{9}[\dX]\z/)

      digits = isbn[0, 9].chars.map(&:to_i)
      check = isbn[-1] == "X" ? 10 : isbn[-1].to_i
      return (digits.each_with_index.sum { |digit, index| (10 - index) * digit } + check) % 11 == 0
    end

    return false unless isbn.match?(/\A(?:978|979)\d{10}\z/)

    total = isbn[0, 12].chars.each_with_index.sum do |digit, index|
      digit.to_i * (index.even? ? 1 : 3)
    end
    (10 - total % 10) % 10 == isbn[-1].to_i
  end

  def assert_unique(values, label)
    duplicates = values.group_by(&:itself)
                       .select { |_value, instances| instances.length > 1 }
                       .keys
    assert_empty duplicates, "duplicate #{label}: #{duplicates.join(', ')}"
  end
end
