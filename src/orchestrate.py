import os
import json
import logging
from typing import Dict, Any

from src.drive.ingestion import fetch_new_transcripts
from src.agent.core import process_transcript

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_manifest(manifest_path: str = "manifest.json") -> Dict[str, Any]:
    if not os.path.exists(manifest_path):
        return {"processed": {}}
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_manifest(manifest: Dict[str, Any], manifest_path: str = "manifest.json"):
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def run_orchestration(dry_run: bool = False, manifest_path: str = "manifest.json"):
    logger.info(f"Starting orchestration pipeline (dry_run={dry_run})")
    
    try:
        new_transcripts = fetch_new_transcripts()
    except Exception as e:
        logger.error(f"Failed to fetch transcripts: {e}")
        return

    logger.info(f"Fetched {len(new_transcripts)} new valid files.")
    
    manifest = load_manifest(manifest_path)
    processed = manifest.get("processed", {})
    
    for transcript in new_transcripts:
        file_id = transcript["file_id"]
        filename = transcript["filename"]
        content = transcript["content"]
        content_hash = transcript["content_hash"]
        domain = transcript["domain"]
        
        logger.info(f"Processing file: {filename} (ID: {file_id}, Domain: {domain})")
        
        if domain is None:
            logger.info(f"Skipping unclassified file: {filename}")
            processed[file_id] = {
                "status": "skipped_unclassified",
                "content_hash": content_hash,
            }
            continue
            
        # Safety check: skip if already processed with same hash
        if file_id in processed and processed[file_id].get("content_hash") == content_hash:
            logger.info(f"Skipping already processed file: {filename}")
            continue

        try:
            results = process_transcript(content, dry_run=dry_run)
            
            file_status = "success"
            needs_review_payloads = []
            
            for res in results:
                status = res.get("status")
                if status == "needs_review":
                    file_status = "needs_review"
                    needs_review_payloads.append(res)
                    
            if file_status == "needs_review":
                logger.warning(f"File {filename} needs review. Flags: {len(needs_review_payloads)}")
                processed[file_id] = {
                    "status": "needs_review",
                    "content_hash": content_hash,
                    "payloads": needs_review_payloads
                }
            else:
                logger.info(f"File {filename} processed successfully.")
                processed[file_id] = {
                    "status": "success",
                    "content_hash": content_hash
                }
                
        except Exception as e:
            logger.error(f"Transient error processing {filename}: {e}", exc_info=True)
            continue
            
    if not dry_run:
        manifest["processed"] = processed
        save_manifest(manifest, manifest_path)
    else:
        logger.info("Dry run complete. Manifest would have been updated.")

if __name__ == "__main__":
    run_orchestration(dry_run=False)
