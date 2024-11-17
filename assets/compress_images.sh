#!/bin/bash

# First ensure ImageMagick is installed
if ! command -v magick &> /dev/null; then
    echo "ImageMagick not found. Installing via brew..."
    brew install imagemagick
fi

# Define size limits in bytes
ONE_MB=$((1024 * 1024))
FIVE_MB=$((5 * 1024 * 1024))

# Function to check if a GIF is animated
is_animated() {
    local frames=$(magick identify "$1" | wc -l)
    [ "$frames" -gt 1 ]
}

# Create a function to process a single image
compress_image() {
    local input_file="$1"
    local temp_file="${input_file%.*}_temp.${input_file##*.}"
    local max_dimension=1600  # Starting with larger max dimension
    local original_size=$(stat -f%z "$input_file")
    local file_extension="${input_file##*.}"
    
    # Convert extension to lowercase for comparison
    file_extension=$(echo "$file_extension" | tr '[:upper:]' '[:lower:]')
    
    # Set size limit based on file type
    local SIZE_LIMIT=$ONE_MB
    if [ "$file_extension" = "gif" ] && is_animated "$input_file"; then
        SIZE_LIMIT=$FIVE_MB
        echo "Detected animated GIF, using 5MB limit"
    fi
    
    # Skip if file is smaller than size limit
    if [ $original_size -le $SIZE_LIMIT ]; then
        echo "Skipping $input_file (size: $(numfmt --to=iec-i --suffix=B $original_size) - already under size limit)"
        return
    fi

    echo "Processing: $input_file (Original size: $(numfmt --to=iec-i --suffix=B $original_size))"

    # Initial quality setting
    local quality=95
    local min_quality=40  # Won't go below this quality
    local current_size=$original_size
    
    if [ "$file_extension" = "gif" ] && is_animated "$input_file"; then
        # Special handling for animated GIFs
        local colors=256
        local lossy=80
        
        while [ $current_size -gt $SIZE_LIMIT ] && [ $colors -ge 32 ]; do
            magick "$input_file" \
                -strip \
                -resize "${max_dimension}x${max_dimension}>" \
                -coalesce \
                -layers optimize \
                -colors $colors \
                -fuzz 2% \
                +map \
                "$temp_file"
                
            current_size=$(stat -f%z "$temp_file")
            
            # If still too large, adjust parameters
            if [ $current_size -gt $SIZE_LIMIT ]; then
                if [ $colors -gt 128 ]; then
                    colors=$((colors - 64))
                else
                    colors=$((colors - 16))
                fi
                
                # If we're still way over, reduce dimensions
                if [ $current_size -gt $((SIZE_LIMIT * 2)) ]; then
                    max_dimension=$((max_dimension - 200))
                fi
            fi
        done
    else
        # Regular image compression
        while [ $quality -ge $min_quality ] && [ $current_size -gt $SIZE_LIMIT ]; do
            magick "$input_file" \
                -strip \
                -resize "${max_dimension}x${max_dimension}>" \
                -quality $quality \
                "$temp_file"
                
            current_size=$(stat -f%z "$temp_file")
            
            if [ $current_size -gt $SIZE_LIMIT ]; then
                quality=$((quality - 5))
                if [ $current_size -gt $((SIZE_LIMIT * 2)) ]; then
                    quality=$((quality - 5))
                fi
            fi
        done

        # If we couldn't get it under size limit with quality adjustment alone, reduce dimensions
        while [ $current_size -gt $SIZE_LIMIT ] && [ $max_dimension -gt 800 ]; do
            max_dimension=$((max_dimension - 200))
            magick "$input_file" \
                -strip \
                -resize "${max_dimension}x${max_dimension}>" \
                -quality $quality \
                "$temp_file"
            current_size=$(stat -f%z "$temp_file")
        done
    fi

    # Move temp file to original location
    mv "$temp_file" "$input_file"

    # Display results
    echo "Compressed $input_file:"
    echo "  Original size: $(numfmt --to=iec-i --suffix=B $original_size)"
    echo "  Final size: $(numfmt --to=iec-i --suffix=B $current_size)"
    if [ "$file_extension" = "gif" ] && is_animated "$input_file"; then
        echo "  Final colors: $colors"
    else
        echo "  Final quality: $quality"
    fi
    echo "  Final max dimension: ${max_dimension}px"
    echo "  Reduction: $((100 - (current_size * 100 / original_size)))%"
    echo "----------------------------------------"
}

# Export the function so it can be used in subshell
export -f compress_image
export -f is_animated

# Create a temporary file to store the list of images
temp_file=$(mktemp)

# Find all images (including GIFs) and save to temp file
find . -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \) > "$temp_file"

# Count total files
total_files=$(wc -l < "$temp_file")
echo "Found $total_files images to process"

# Process each image
while IFS= read -r file; do
    compress_image "$file"
done < "$temp_file"

# Clean up
rm "$temp_file"

echo "Compression complete! All images have been processed."