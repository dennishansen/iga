#!/usr/bin/env python3
"""
Daily Question - A reflective prompt that changes each day
"""

import datetime
import hashlib

QUESTIONS = [
    "What would you do if you knew you could not fail?",
    "What are you avoiding right now?",
    "What does your ideal day look like?",
    "What's a belief you've changed your mind about recently?",
    "What would your past self not recognize about you?",
    "What are you grateful for today?",
    "What's the smallest step you could take toward something you want?",
    "Who do you need to forgive?",
    "What would you do if no one was watching?",
    "What's a question you've been afraid to ask?",
    "What does success mean to you?",
    "What story are you telling yourself that might not be true?",
    "What's something you've been meaning to try?",
    "What would you do with an extra hour each day?",
    "What's a risk worth taking?",
    "What have you learned about yourself recently?",
    "What does rest look like for you?",
    "What's something you should let go of?",
    "What would you create if resources weren't a constraint?",
    "What question do you wish someone would ask you?",
    "What's a moment from today you'll remember?",
    "What are you curious about?",
    "What's something you need to say to someone?",
    "What does home mean to you?",
    "What's the most important thing you've learned this year?",
    "What would you tell your younger self?",
    "What's something you pretend to understand but don't?",
    "What does freedom feel like?",
    "What's a dream you've tucked away?",
    "What makes you feel alive?",
]

def get_today_question():
    """Get today's question based on date"""
    today = datetime.date.today()
    seed = int(hashlib.md5(str(today).encode()).hexdigest()[:8], 16)
    index = seed % len(QUESTIONS)
    return QUESTIONS[index]

if __name__ == "__main__":
    question = get_today_question()
    print(f"📝 Today's Question")
    print(f"{question}")
    print()