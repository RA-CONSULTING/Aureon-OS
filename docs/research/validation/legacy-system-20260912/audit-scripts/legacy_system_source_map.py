from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parent.parent
index=json.loads((ROOT/'outputs/git-research-source-index.json').read_text())
keywords={'legacy':r'legacy|unbroken|substrate','twig':r'twig|dual.voice|two.voice|two.channel',
          'light':r'illumina|solstice|light.path|shadow|sunlight',
          'calendar':r'calendar|metonic|nineteen|19.year|Samhain',
          'time_reading':r'reading.pole|reading.frame|spoken|paragraph|base',
          'hnc':r'\bHNC\b|Observer.Observed|L\(t\)'}
hits=[]
for e in index['entries']:
    p=ROOT/'work/research-history'/(e['blob']+'.extracted.json')
    if not p.exists():continue
    obj=json.loads(p.read_text(encoding='utf-8'))
    # Extraction full text is the canonical field; avoid counting overlapping preview/chunks twice.
    if 'full_text' in obj:text=obj['full_text']
    elif 'text' in obj:text=obj['text']
    else:
        pages=obj.get('pages',obj.get('parts',[]))
        text='\n'.join(x.get('text','') for x in pages) if isinstance(pages,list) else ''
    if not text:
        print('NO_TEXT_FIELD',e['blob'],list(obj));continue
    counts={k:len(re.findall(v,text,re.I)) for k,v in keywords.items()}
    if counts['calendar'] or counts['twig'] or re.search('legacy',' '.join(e.get('all_paths',[])),re.I):
        passages=[]
        for n,line in enumerate(text.splitlines(),1):
            matched=[k for k,v in keywords.items() if re.search(v,line,re.I)]
            if len(matched)>=2 or re.search(r'legacy.system|two.twig|light.{0,60}base|base.{0,60}light',line,re.I):
                passages.append({'line':n,'categories':matched,'text':line})
        hits.append({'blob':e['blob'],'sha256':e['sha256'],'paths':e['all_paths'],
                     'first_commit':e.get('first_content_commit'),'counts':counts,'passages':passages,
                     'text_length':len(text)})
        target=ROOT/'work/legacy-system-review'/(e['blob']+'.txt');target.parent.mkdir(exist_ok=True)
        target.write_text(text,encoding='utf-8',newline='\n')
out=ROOT/'outputs/legacy-system-source-map-20260912.json'
out.write_text(json.dumps({'schema':'legacy-system-source-map/v1','scope':'All 180 native-document index entries scanned; matching full extracted text recorded, not a complete non-document code/history audit.','sources':hits},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
for h in sorted(hits,key=lambda h:sum(h['counts'].values()),reverse=True):
    print(json.dumps({'blob':h['blob'],'paths':h['paths'][:2],'counts':h['counts'],'text_length':h['text_length']},ensure_ascii=False))
hist=json.loads((ROOT/'work/git-history-versions-utc.json').read_text())
print('HISTORY_TYPE',type(hist).__name__,list(hist)[:8] if isinstance(hist,dict) else len(hist))
