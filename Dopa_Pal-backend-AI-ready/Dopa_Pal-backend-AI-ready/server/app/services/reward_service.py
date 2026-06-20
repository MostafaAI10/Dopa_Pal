import random
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.task import SubBlock, Task
from app.models.reward import Reward

# Mock vault facts representing curated dopamine spikes for learning
INTEREST_VAULT = {
    "architecture": [
        "Did you know? The first computer bug was a real moth found trapped in a relay by Grace Hopper in 1947.",
        "Monolithic architectures aren't anti-patterns; they are often the fastest way to validate product-market fit before scaling to microservices."
    ],
    "cybersecurity": [
        "In 1988, the Morris Worm became the first widely recognized internet worm, infecting roughly 10% of all connected computers at the time.",
        "Multi-factor authentication (MFA) blocks 99.9% of automated account takeover attacks."
    ],
    "languages": [
        "German compound words can be incredibly long. 'Kraftfahrzeug-Haftpflichtversicherung' means automobile liability insurance.",
        "Syntax is what binds language semantics; in coding languages, syntax is strict, whereas human languages tolerate colloquial faults."
    ]
}

THEMES = [
    {"accent": "#27dddf", "name": "Cyber Cyan"},
    {"accent": "#ff6b6b", "name": "Sunset Peach"},
    {"accent": "#a8a5e6", "name": "Retro Lavender"},
    {"accent": "#51cf66", "name": "Mint Focus"}
]

def complete_sub_block(db: Session, user_id: int, sub_block_id: int) -> Dict[str, Any]:
    # Fetch subblock
    sub_block = db.query(SubBlock).filter(SubBlock.id == sub_block_id).first()
    if not sub_block:
        return {"error": "Sub-block not found"}
        
    # Mark completed
    sub_block.status = "completed"
    sub_block.completed_at = datetime.utcnow()
    
    # Check parent task
    task = db.query(Task).filter(Task.id == sub_block.task_id, Task.user_id == user_id).first()
    if not task:
        db.commit()
        return {"error": "Parent task not found or user unauthorized"}
        
    # Check if all subblocks of the task are complete
    total_blocks = db.query(SubBlock).filter(SubBlock.task_id == task.id).count()
    completed_blocks = db.query(SubBlock).filter(
        SubBlock.task_id == task.id,
        SubBlock.status == "completed"
    ).count()
    
    if total_blocks == completed_blocks:
        task.status = "completed"
        
    # Determine if reward is unlocked (e.g. 25% chance per block or based on completion milestones)
    unlocked_theme = None
    unlocked_reward = None
    if random.random() < 0.5: # 50% chance to unlock theme customization or accent
        chosen_theme = random.choice(THEMES)
        # Store reward
        unlocked_reward = Reward(
            user_id=user_id,
            type="theme",
            metadata_json={"theme_accent": chosen_theme["accent"], "theme_name": chosen_theme["name"]}
        )
        db.add(unlocked_reward)
        unlocked_theme = chosen_theme
        
    # Check Interest Vault drop
    vault_drop = None
    if task.interest_tag and task.interest_tag.lower() in INTEREST_VAULT:
        vault_drop = random.choice(INTEREST_VAULT[task.interest_tag.lower()])
        # Store interest drop reward
        db.add(Reward(
            user_id=user_id,
            type="interest_drop",
            metadata_json={"tag": task.interest_tag, "fact": vault_drop}
        ))
        
    db.commit()
    
    return {
        "status": "success",
        "sub_block_id": sub_block_id,
        "task_completed": task.status == "completed",
        "unlocked_theme": unlocked_theme,
        "interest_vault_fact": vault_drop
    }
