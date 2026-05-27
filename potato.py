import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import html2text
from bs4 import BeautifulSoup

# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_DIR = "/sec"  # Your root directory

# ==========================================
# 2. BOILERPLATE CLEANING & PARSING WORKER
# ==========================================
def clean_and_convert_file(input_path, output_path):
    """Processes a single file: strips boilerplate, converts HTML to Markdown."""
    try:
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()

        # Improvement A: Strip the heavy SEC metadata header wrapper
        # We throw away everything above the first <DOCUMENT> tag
        match = re.search(r'<DOCUMENT>', raw_content, re.IGNORECASE)
        if match:
            raw_content = raw_content[match.start():]

        # Parse HTML elements safely using the fast lxml engine
        soup = BeautifulSoup(raw_content, 'lxml')
        for element in soup(["script", "style", "textarea"]):
            element.decompose()
        
        clean_html = str(soup)

        # Configure the HTML-to-Markdown engine
        converter = html2text.HTML2Text()
        converter.body_width = 0  # Crucial: Prevents lines from cutting off mid-sentence
        converter.ignore_links = True
        converter.ignore_images = True
        converter.images_to_alt = False
        
        # Translate HTML markup to structured Markdown
        markdown_text = converter.handle(clean_html)

        # Improvement B: Regex cleanups for navigation junk & standalone page numbers
        # Remove standalone page numbers (e.g., "Page 12" or "12" on its own line)
        markdown_text = re.sub(r'^\s*(page\s+)?\d+\s*$', '', markdown_text, flags=re.M)
        # Remove "Table of Contents" and "Index to..." lines
        markdown_text = re.sub(r'(?i)^\s*table of contents\s*$', '', markdown_text, flags=re.M)
        markdown_text = re.sub(r'(?i)^\s*index to.*$', '', markdown_text, flags=re.M)
        
        # Collapse excessive blank vertical space
        markdown_text = re.sub(r'\n\s*\n', '\n\n', markdown_text)

        # Save out the beautifully optimized file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text.strip())
            
        return True, input_path
    except Exception as e:
        return False, f"{input_path} -> {str(e)}"

# ==========================================
# 3. MULTI-PROCESSING ORCHESTRATOR
# ==========================================
def main():
    print(f"Scanning '{BASE_DIR}' to construct the parallel task queue...")
    tasks = []

    # Gather all outstanding jobs first
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            # Match raw text files, skip previously processed clean text/markdown files
            if file.endswith('.txt') and not file.endswith('_cleaned.txt') and not file.endswith('.md'):
                input_full_path = os.path.join(root, file)
                output_full_path = os.path.splitext(input_full_path)[0] + ".md"
                
                # Resumable: If the Markdown file already exists, skip it!
                if not os.path.exists(output_full_path):
                    tasks.append((input_full_path, output_full_path))

    total_tasks = len(tasks)
    if total_tasks == 0:
        print("No new files found to convert. Pipeline is already up to date!")
        return

    print(f"Found {total_tasks} files requiring conversion.")
    # Automatically scales to use 100% of your available CPU cores
    # Leaves 2 cores free for the system, but always utilizes at least 1 core
    num_workers = max(1, os.cpu_count() - 2)
    print(f"Spawning parallel pipeline across all {num_workers} CPU cores...")

    start_time = time.time()
    success_count = 0
    failure_count = 0

    # Execute the tasks concurrently across available CPU cores
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks to the process pool
        futures = {executor.submit(clean_and_convert_file, inp, out): inp for inp, out in tasks}
        
        # Monitor completion as workers finish their files
        for i, future in enumerate(as_completed(futures), 1):
            success, meta = future.result()
            if success:
                success_count += 1
            else:
                failure_count += 1
                with open("parallel_parsing_errors.log", "a") as log:
                    log.write(meta + "\n")
            
            # Print status update every 50 files to keep terminal output responsive but efficient
            if i % 50 == 0 or i == total_tasks:
                pct = (i / total_tasks) * 100
                print(f"Progress: [{i}/{total_tasks}] ({pct:.1f}%) | Success: {success_count} | Failed: {failure_count}")

    end_time = time.time()
    elapsed_mins = (end_time - start_time) / 60
    print(f"\n🎉 Parallel processing suite finished execution!")
    print(f"Total Time: {elapsed_mins:.2f} minutes")
    print(f"Successfully converted: {success_count} files")
    print(f"Failed conversions: {failure_count} (Detailed inside 'parallel_parsing_errors.log')")

if __name__ == '__main__':
    main()