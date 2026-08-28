#!/usr/bin/env python3
"""Parse breakout session data from the full catalog text file."""
import re
import json

WAITLIST_CODES = {'CLOB1046LV', 'CLOB1084LV', 'CLOB1215LV', 'CLOB1224LV', 'CLOB1266LV', 'INVB1153LV'}

def determine_track(code):
    if code.startswith('APP'):
        return 'App Modernization'
    elif code.startswith('CLO'):
        return 'Cloud Infrastructure'
    elif code.startswith('INV'):
        return 'Innovation'
    elif code.startswith('SEC'):
        return 'Security'
    return 'Other'

def parse_full_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by session code pattern to find sessions
    # Pattern: title [CODE]
    pattern = r'([^\n]+?)\s*\[([A-Z]{3,5}\d+LV[S]?)\]'
    matches = list(re.finditer(pattern, content))
    
    sessions = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        code = match.group(2).strip()
        
        # Get text between this match and next match
        start = match.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(content)
        block = content[start:end]
        
        # Extract day and time
        day_match = re.search(r'(Monday|Tuesday|Wednesday),\s*(Aug \d+|Sep \d+)', block)
        time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)\s*PDT', block)
        
        day = ''
        if day_match:
            weekday = day_match.group(1)[:3]
            date = day_match.group(2)
            day = f"{weekday} {date}"
        
        time_start = time_match.group(1) if time_match else ''
        time_end = time_match.group(2) if time_match else ''
        
        # Determine properties
        track = determine_track(code)
        is_sponsored = 1 if code.endswith('LVS') or 'Sponsor Session' in content[max(0, match.start()-100):match.start()] else 0
        is_peoples_choice = 1 if "People's Choice" in content[max(0, match.start()-100):match.start()] else 0
        availability = 'Waitlist' if code in WAITLIST_CODES else 'Available'
        
        # Extract description (first sentence after code)
        desc_match = re.search(r'\n\n(.+?)(?:\.\.\.|$)', block, re.DOTALL)
        description = ''
        if desc_match:
            description = desc_match.group(1).strip()[:300]
        
        sessions.append({
            'code': code,
            'title': title,
            'track': track,
            'day': day,
            'time_start': time_start,
            'time_end': time_end,
            'description': description,
            'is_peoples_choice': is_peoples_choice,
            'is_sponsored': is_sponsored,
            'availability': availability
        })
    
    return sessions

if __name__ == '__main__':
    sessions = parse_full_file('/home/tono/work/kiro/202608_Explore_LasVegas/breakout-list-full.txt')
    
    # Deduplicate by code (some sessions repeat for multiple days)
    seen = {}
    for s in sessions:
        if s['code'] not in seen:
            seen[s['code']] = s
        else:
            # If we already have it but this one has a different day, note it
            existing = seen[s['code']]
            if s['day'] and s['day'] != existing['day']:
                existing['day'] = existing['day'] + '; ' + s['day']
    
    unique_sessions = list(seen.values())
    print(f"Total unique sessions: {len(unique_sessions)}")
    
    # Output as JSON for SQLite import
    with open('/home/tono/work/kiro/202608_Explore_LasVegas/sessions_parsed.json', 'w', encoding='utf-8') as f:
        json.dump(unique_sessions, f, ensure_ascii=False, indent=2)
    
    print("Saved to sessions_parsed.json")
    
    # Summary
    tracks = {}
    waitlist_count = 0
    for s in unique_sessions:
        tracks[s['track']] = tracks.get(s['track'], 0) + 1
        if s['availability'] == 'Waitlist':
            waitlist_count += 1
    
    print(f"\nBy Track:")
    for t, c in sorted(tracks.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    print(f"\nWaitlist: {waitlist_count}")
    print(f"Available: {len(unique_sessions) - waitlist_count}")
