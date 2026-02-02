#!/usr/bin/env python3
"""
One-time cleanup script to remove existing PDF and markdown files from uploads folder.
The important JSON data is preserved in the database.
"""
import os
import glob
from pathlib import Path

def cleanup_existing_uploads():
    """Remove all existing PDF and markdown files from uploads folder."""
    upload_folder = "uploads"
    
    if not os.path.exists(upload_folder):
        print("❌ Uploads folder not found")
        return
    
    # Find all PDF and markdown files
    pdf_files = glob.glob(os.path.join(upload_folder, "*.pdf"))
    md_files = glob.glob(os.path.join(upload_folder, "*_final.md"))
    
    all_files = pdf_files + md_files
    
    print(f"🔍 Found {len(pdf_files)} PDF files and {len(md_files)} markdown files")
    print(f"📁 Total files to delete: {len(all_files)}")
    
    if len(all_files) == 0:
        print("✅ No files to clean up")
        return
    
    # Ask for confirmation
    response = input(f"\n⚠️  This will permanently delete {len(all_files)} files. Continue? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cleanup cancelled")
        return
    
    # Delete files
    deleted_count = 0
    failed_count = 0
    
    for file_path in all_files:
        try:
            os.remove(file_path)
            deleted_count += 1
            print(f"✅ Deleted: {os.path.basename(file_path)}")
        except Exception as e:
            failed_count += 1
            print(f"❌ Failed to delete {os.path.basename(file_path)}: {e}")
    
    print(f"\n📊 Cleanup Summary:")
    print(f"   ✅ Successfully deleted: {deleted_count} files")
    print(f"   ❌ Failed to delete: {failed_count} files")
    
    if deleted_count > 0:
        # Calculate approximate space saved (rough estimate)
        print(f"   💾 Approximate space saved: {deleted_count * 0.5:.1f} MB (estimated)")
    
    print(f"\n🎉 Cleanup completed! Your server storage is now optimized.")
    print(f"📝 Note: All important JSON data remains safely stored in the database.")

if __name__ == "__main__":
    cleanup_existing_uploads()
