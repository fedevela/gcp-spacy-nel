#!/bin/bash

# Check if a path argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <path>"
  exit 1
fi

# Set the provided path as the target directory
TARGET_DIR="$1"

# Create or clear the project.txt file
echo "The following text file contains a complete project submission. The file is structured using clear delimiters to separate different files and their contents. The delimiters are formatted as follows:" > "$TARGET_DIR/project.txt"
echo "Beginning of a File Section: <<<<<< BEGIN <file_path> >>>>>>" >> "$TARGET_DIR/project.txt"
echo "End of a File Section: <<<<<< END <file_path> >>>>>>" >> "$TARGET_DIR/project.txt"
echo "" >> "$TARGET_DIR/project.txt"
echo "Contents:" >> "$TARGET_DIR/project.txt"

# Run the tree command on the specified directory and append output to project.txt
tree -I 'dist|build|venv|cache|node_modules|ios|\.gradle|\.git|\.nx|project.txt|package-lock.json|*.ico|*.png|*.jpg|*.jpeg|*.gif|*.jar|*.bin|*.exe|*.dll|*.class|*.so|*.dylib|*.zip|*.tar.gz|*.7z|*.log|*.map|*.svg|requirements.txt|*.keystore|*.idea' "$TARGET_DIR" >> "$TARGET_DIR/project.txt"

# Use find command to locate files, excluding specified paths, and append each file's content to project.txt
for file in $(find "$TARGET_DIR" -type f \
  ! \( \
    -path "*/dist/*" \
    -o -path "*/build/*" \
    -o -path "*/venv/*" \
    -o -path "*gradlew*" \
    -o -path "*/cache/*" \
    -o -path "*/node_modules/*" \
    -o -path "*/ios/*" \
    -o -path "*/.gradle/*" \
    -o -path "*/.git/*" \
    -o -path "*/network_security_config.xml" \
    -o -path "*/.nx/*" \
    -o -name "project.txt" \
    -o -name "package-lock.json" \
    -o -path "*/.idea/*" \
    -o -name "*.ico" \
    -o -name "*.png" \
    -o -name "*.jpg" \
    -o -name "*.jpeg" \
    -o -name "*.gif" \
    -o -name "*.jar" \
    -o -name "*.bin" \
    -o -name "*.exe" \
    -o -name "*.dll" \
    -o -name "*.class" \
    -o -name "*.so" \
    -o -name "*.dylib" \
    -o -name "*.zip" \
    -o -name "*.tar.gz" \
    -o -name "*.7z" \
    -o -name "*.log" \
    -o -name "*.map" \
    -o -name "*.svg" \
    -o -name "requirements.txt" \
    -o -name "*.keystore" \
  \) ); do
    echo "<<<<<< BEGIN $file >>>>>>>" >> "$TARGET_DIR/project.txt"
    cat "$file" >> "$TARGET_DIR/project.txt"
    echo "<<<<<< END $file >>>>>>>" >> "$TARGET_DIR/project.txt"
done
