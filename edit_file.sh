#!/bin/bash

# Usage: ./edit_file.sh [file] [operation] [args]

file=$1
operation=$2

case $operation in
  search_replace)
    search_text=$3
    replace_text=$4
    sed -i "s/$search_text/$replace_text/g" "$file"
    ;;
  add_line)
    line_number=$3
    line_text=$4
    sed -i "${line_number}i $line_text" "$file"
    ;;
  remove_line)
    line_number=$3
    sed -i "${line_number}d" "$file"
    ;;
  *)
    echo "Invalid operation. Supported operations: search_replace, add_line, remove_line"
    exit 1
    ;;
esac
