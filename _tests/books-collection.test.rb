# frozen_string_literal: true

require "date"
require "minitest/autorun"
require "pathname"
require "yaml"

class BooksCollectionTest < Minitest::Test
  ROOT = Pathname(__dir__).parent
  BOOK_PATHS = Dir[ROOT.join("_books/*.md")].sort.freeze
  STATUSES = %w[read want_to_read].freeze

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

      isbn = book["isbn"].to_s
      assert_match(/\A(?:\d{9}[\dX]|\d{13})\z/, isbn, "#{path}: invalid ISBN") unless isbn.empty?

      next if book["cover"].to_s.empty?

      cover = ROOT.join(book.fetch("cover").delete_prefix("/"))
      assert cover.file?, "#{path}: missing cover #{cover}"
    end
  end

  def test_titles_and_isbns_are_unique
    assert_unique books.map { |book| book.fetch("title") }, "title"
    assert_unique books.filter_map { |book| book["isbn"] }, "ISBN"
  end

  def test_books_page_is_only_a_shell
    page = ROOT.join("_pages/books.md").read
    refute_includes page, "window.__BOOKS"
    refute_includes page, '"synopsis"'
  end

  private

  def assert_unique(values, label)
    duplicates = values.tally.select { |_value, count| count > 1 }.keys
    assert_empty duplicates, "duplicate #{label}: #{duplicates.join(', ')}"
  end
end
