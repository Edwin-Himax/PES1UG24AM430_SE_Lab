# Skyscraper Stack Repair Lab

This project is a precision timing and balance tower stacking game using **Pygame**. It introduces students to 1D bounding-box intersection math, dynamic geometry slicing, vertical camera offset scrolling, and escalating difficulty curves within an object-oriented codebase.
---

## What's Provided

A working Skyscraper Stack game with:

- A foundation block positioned at the base of the arena
- Horizontally oscillating active blocks that bounce between screen boundaries at escalating speeds
- Precision placement triggered via `Space` key or left mouse click
- Automatic dynamic width trimming based on overlap alignment against the previous tier
- Downward camera scrolling when the stack exceeds the vertical threshold
- A Game Over collapse screen displaying total tower height with instant restart functionality

It has **one deliberate bug** and **three optional features** left as tasks to implement. You are expected to **analyze**, **interact with an AI assistant**, and **complete/fix** the game to make it fully functional and more interesting.

### **Use an LLM (e.g. ChatGPT or Claude) as your debugging and pair-programming partner for this lab.**
---

## Getting Started

### Setup

1. Make sure you have Python 3.10+ installed.
2. Install dependencies:

```bash
pip install pygame
```

3. Run the game:

```bash
python main.py
```

**Controls:** Press Space or Left-Click to drop the active block. Press Space or R to restart after Game Over.


## Tasks to Complete

Each task must be completed using an iterative process involving LLM suggestions and your critical code review.

### Task 1: Fix the inverted overlap placement bug

Landing a block directly on top of the tower results in an immediate game over, whereas dropping a block into empty air allows the tower to continue building upward. Correct the drop condition so valid overlaps securely stack onto the tower while complete misses trigger the tower collapse.

### Task 2: Implement "Perfect Placement" bonus & width restoration

Currently, any placement slightly off-center permanently shaves down the block's width. Introduce a precision reward: if a dropped block aligns almost flush with the top of the tower, snap it into place without trimming, show a "PERFECT!" prompt with bonus score, and slightly restore lost width if multiple perfect drops are landed in a row
 
### Task 3: Implement falling off-cut debris animation

Sliced off-cut sections of blocks disappear instantly from the arena without visual feedback. Add animated debris that creates a falling, rotating remnant of the trimmed overhang whenever a block is cut, giving weight and impact to imperfect placements.

### Task 4: Implement Atmospheric Background Shifting

The sky remains a static color throughout the entire climb regardless of tower height. Transition the background through dynamic atmospheric color gradients as the skyscraper stacks higher

---

## Expected Behavior

- Dropping a block while aligned over the stack trims the edges, places the block, and increases the tower height score.
- Dropping a block outside the stack triggers the TOWER COLLAPSED! game over screen.
- As the stack grows taller, the camera smoothly scrolls downward so the top of the tower remains visible.
- Pressing Space or R on the collapse screen resets the tower and restores base dimensions.

## Folder Structure

```
word_scramble/
├── game/
│   ├── game_engine.py
│   └── text_box.py
├── main.py
└── README.md
```



