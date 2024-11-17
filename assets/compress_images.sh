#!/bin/bash

# First ensure ImageMagick is installed
if ! command -v magick &> /dev/null; then
    echo "ImageMagick not found. Installing via brew..."
    brew install imagemagick
fi

# Define 1MB in bytes
ONE_MB=$((1024 * 1024))

# Create a function to process a single image
compress_image() {
    local input_file="$1"
    local temp_file="${input_file%.*}_temp.${input_file##*.}"
    local max_dimension=1600  # Starting with larger max dimension
    local original_size=$(stat -f%z "$input_file")
    
    # Skip if file is smaller than 1MB
    if [ $original_size -le $ONE_MB ]; then
        echo "Skipping $input_file (size: $(numfmt --to=iec-i --suffix=B $original_size) - already under 1MB)"
        return
    fi

    echo "Processing: $input_file (Original size: $(numfmt --to=iec-i --suffix=B $original_size))"

    # Initial quality setting
    local quality=95
    local min_quality=40  # Won't go below this quality
    local current_size=$original_size
    
    while [ $quality -ge $min_quality ] && [ $current_size -gt $ONE_MB ]; do
        magick "$input_file" \
            -strip \
            -resize "${max_dimension}x${max_dimension}>" \
            -quality $quality \
            "$temp_file"
            
        current_size=$(stat -f%z "$temp_file")
        
        # If still too large, reduce quality for next iteration
        if [ $current_size -gt $ONE_MB ]; then
            quality=$((quality - 5))
            # If we're still way over 1MB, make larger quality jumps
            if [ $current_size -gt $((ONE_MB * 2)) ]; then
                quality=$((quality - 5))
            fi
        fi
    done

    # If we couldn't get it under 1MB with quality adjustment alone, start reducing dimensions
    while [ $current_size -gt $ONE_MB ] && [ $max_dimension -gt 800 ]; do
        max_dimension=$((max_dimension - 200))
        magick "$input_file" \
            -strip \
            -resize "${max_dimension}x${max_dimension}>" \
            -quality $quality \
            "$temp_file"
        current_size=$(stat -f%z "$temp_file")
    done

    # Move temp file to original location
    mv "$temp_file" "$input_file"

    # Display results
    echo "Compressed $input_file:"
    echo "  Original size: $(numfmt --to=iec-i --suffix=B $original_size)"
    echo "  Final size: $(numfmt --to=iec-i --suffix=B $current_size)"
    echo "  Final quality: $quality"
    echo "  Final max dimension: ${max_dimension}px"
    echo "  Reduction: $((100 - (current_size * 100 / original_size)))%"
    echo "----------------------------------------"
}

# Export the function so it can be used in subshell
export -f compress_image

# Create a temporary file to store the list of images
temp_file=$(mktemp)

# Find all JPG, JPEG, and PNG files over 1MB and save to temp file
find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -size +1M > "$temp_file"

# Count total files
total_files=$(wc -l < "$temp_file")
echo "Found $total_files images over 1MB to process"

# Process each image
while IFS= read -r file; do
    compress_image "$file"
done < "$temp_file"

# Clean up
rm "$temp_file"

echo "Compression complete! All images over 1MB have been processed."