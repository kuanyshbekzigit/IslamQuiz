#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Сұрақтар бөліктерін біріктіріп, толық сұрақтар базасын жасау скрипті
"""

import json
import os

def merge_questions():
    """Барлық сұрақтар файлдарын біріктіру"""
    questions = []
    
    # Бірінші бөлік (questions.json)
    if os.path.exists('questions.json'):
        with open('questions.json', 'r', encoding='utf-8') as file:
            part1 = json.load(file)
            questions.extend(part1)
            print(f"questions.json: {len(part1)} сұрақ қосылды")
    
    # Екінші бөлік (questions_part2.json)
    if os.path.exists('questions_part2.json'):
        with open('questions_part2.json', 'r', encoding='utf-8') as file:
            part2 = json.load(file)
            questions.extend(part2)
            print(f"questions_part2.json: {len(part2)} сұрақ қосылды")
    
    # Үшінші бөлік (questions_part3.json)
    if os.path.exists('questions_part3.json'):
        with open('questions_part3.json', 'r', encoding='utf-8') as file:
            part3 = json.load(file)
            questions.extend(part3)
            print(f"questions_part3.json: {len(part3)} сұрақ қосылды")
    
    # Толық сұрақтар базасын сақтау
    with open('questions_full.json', 'w', encoding='utf-8') as file:
        json.dump(questions, file, ensure_ascii=False, indent=4)
    
    print(f"Барлығы: {len(questions)} сұрақ біріктірілді")
    print("Нәтиже: questions_full.json файлына сақталды")

if __name__ == "__main__":
    merge_questions() 