#!/usr/bin/env python3
"""QuickBooks "Customer Contact List" (.xlsx) → pp_import_apply.py CSV + review CSV (Puddle Jumper 19/11). Read-only.

    python3 scripts/pp_import_quickbooks.py <list.xlsx> <out-ghl.csv> <out-review.csv> [own-domain]
    python3 scripts/pp_import_apply.py <out-ghl.csv> --only "<account>" [--apply]

Name from "Full name" (address junk after "-" cut); "Customer:Job" sub-customers and rows sharing a phone/e-mail are
merged into the first contact (other entries go to its notes); Mobile preferred over Phone; address split into street /
city / state / ZIP (AZ typos fixed); other pool companies tagged "b2b pool company"; rows without phone and e-mail,
test rows and the business own e-mail skipped. Tags: existing customer, quickbooks import. Client data: keep out of git.
"""
import openpyxl, re, csv, sys, collections
src, out, review = sys.argv[1:4]
OWN = sys.argv[4].lower() if len(sys.argv) > 4 else ""  # business e-mail domain, e.g. puddlejumperaz.com
CITIES = ["Apache Junction","San Tan Valley","Queen Creek","Gold Canyon","Sun Lakes","Casa Grande","Fountain Hills","Paradise Valley",
 "Mesa","Gilbert","Chandler","Phoenix","Tempe","Scottsdale","Glendale","Peoria","Maricopa","Florence","Ahwatukee","Surprise","Goodyear",
 "Avondale","Buckeye","Tucson","Higley","Coolidge","Laveen","Cave Creek","Tolleson"]
STATES = {"az":"AZ","arizona":"AZ","ariz":"AZ"}
def sq(s): return re.sub(r"\s+"," ",str(s or "").replace("\xa0"," ")).strip()
def tc(s):
    s=sq(s)
    if s.isupper() or s.islower():
        return " ".join(w.lower() if re.fullmatch(r"\d+(st|nd|rd|th)",w,re.I) else (w.upper() if w.lower() in ("ne","nw","se","sw","llc","hoa") else w.capitalize()) for w in s.split())
    return s
def phones(s):
    s=str(s or ""); res=[]
    for lab,val in re.findall(r"(Phone|Mobile|Fax|Alt\.? ?Phone|Home|Work)?\s*:?\s*([+\d][\d\s().+-]{8,}\d)",s):
        d=re.sub(r"\D","",val)
        if len(d)==11 and d[0]=="1": d=d[1:]
        ok=len(d)==10 and d[0] not in "01"
        res.append(((lab or "").lower(), "+1"+d if ok else "", val.strip()))
    return res
FIX={"chander":"Chandler","chandle":"Chandler","queen creekk":"Queen Creek","qc":"Queen Creek","santan valley":"San Tan Valley",
 "san an valley":"San Tan Valley","phx":"Phoenix","phoeniz":"Phoenix","pboenix":"Phoenix","meds":"Mesa","mess":"Mesa","sunlakes":"Sun Lakes",
 "foumtain hills":"Fountain Hills","trmpe":"Tempe","apache jct":"Apache Junction","santan":"San Tan Valley"}
OTHER=["Sun City","Bullhead City","Seattle","San Jose","Spokane","Jamestown","Winnipeg"]
def addr(s):
    s=sq(s)
    if s.upper() in ("N/A","NA","-"): return "","","",""
    s=re.sub(r",?\s*(United States|USA|US|Canada)\.?$","",s,flags=re.I).strip(" ,")
    s=re.sub(r"\(AZ\)|- Arizona","",s).strip()
    z=""; m=re.search(r"\b(\d{5,6})(-\d{4})?(\s+\1)?$",s)
    if m:
        z=m.group(1); s=s[:m.start()].strip(" ,")
        if len(z)==6: z=z[:3]+z[4:] if z[3]=="0" else z[:5]
    st=""; m=re.search(r",?\s*\b([A-Za-z]{2,3}|Arizona|ARIZONA)\.?$",s)
    if m and (m.group(1).lower() in ("az","arizona","as","ad","iaz","arz","ca","wa","nd","mb","ariz")):
        st=m.group(1).upper(); s=s[:m.start()].strip(" ,")
        m2=re.search(r",?\s*\b(AZ|Az)$",s)
        if m2: s=s[:m2.start()].strip(" ,")
    if z.startswith(("85","86")) or st in ("AS","AD","IAZ","ARZ","ARIZONA","ARIZ"): st="AZ"
    if not st and not z and re.search(r"\b(QC|Phx|Mesa|Gilbert|Chandler)$",s,re.I): st="AZ"
    city=""
    for c in CITIES+OTHER+list(FIX):
        m=re.search(r"(^|[\s,])"+re.escape(c)+r",?$",s,re.I)
        if m: city=FIX.get(c.lower(),c); s=s[:m.start()].strip(" ,"); break
    if city and city not in OTHER: st=st or "AZ"
    if city and re.search(r"\b"+re.escape(city)+r",?$",s,re.I):
        s=re.sub(r",?\s*"+re.escape(city)+r",?$","",s,flags=re.I).strip(" ,")
    if "," in s:  # "7431 E Norwood St, Mesa, AZ 85207"
        s=s.split(",")[0].strip()
        if city: s=re.sub(r"\s+"+re.escape(city)+r"$","",s,flags=re.I).strip()
    half=len(s)//2
    if len(s)%2==0 and s[:half].lower()==s[half:].lower(): s=s[:half]
    return tc(s), city, st, z

wb=openpyxl.load_workbook(src,read_only=True); rows=list(wb.active.iter_rows(values_only=True))
hdr=[sq(h) for h in rows[2]]; data=[dict(zip(hdr,r)) for r in rows[3:] if r[0] and not str(r[0]).strip().startswith(("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"))]
COMP=re.compile(r"\b(llc|lllc|inc|properties|property|hoa|rentals?|management|mgmt|association|apartments|trust|company|co\.|corp|pools?|realty|homes|investments?|church|school|club|resort|condos?)\b",re.I)
outrows=[]; flags=collections.defaultdict(list); seen={}
for i,r in enumerate(data, start=4):
    cust=sq(r["Customer full name"]); full=sq(r["Full name"])
    notes=[]
    cust_name, _, cust_extra = cust.partition(":")
    if cust_extra: notes.append(f"QuickBooks name: {cust}")
    full_clean=re.sub(r"\s*-\s*\d+.*$","",full).strip()   # "Jeff Eder-3713 E Redfield Rd"
    if full!=full_clean: notes.append(f"QuickBooks full name: {full}")
    company=""
    if COMP.search(cust_name): company=tc(cust_name)
    name = full_clean or re.sub(r"^[A-Z]{1,3}-\s*\d+\s+\S+(\s+\S+){0,3}\s+(?=[A-Z][a-z])","",cust_name)  # "AA- 2506 N Pinnule Cir Jim Gerhardt"
    if not full_clean and company: name=""
    parts=tc(name).split()
    first=" ".join(parts[:-1]) if len(parts)>1 else (parts[0] if parts else ""); last=parts[-1] if len(parts)>1 else ""
    if not first and company: first=company
    ph=phones(r["Phone numbers"]); valid=[p for p in ph if p[1]]
    mob=[p for p in valid if p[0]=="mobile"]; pri=(mob or [p for p in valid if p[0]!="fax"] or [("", "", "")])[0][1]
    others=sorted({p[1] for p in valid if p[1]!=pri and p[0]!="fax"})
    if r["Phone numbers"] and re.search(r"[A-Za-z]{3,}",re.sub(r"(Phone|Mobile|Fax):","",str(r["Phone numbers"]))):
        notes.append(f"QuickBooks phone note: {sq(r['Phone numbers'])}")
    em=sq(r["Email"]).lower(); ems=[e for e in re.split(r"[,; ]+",em) if "@" in e]; em=ems[0] if ems else ""
    a1,city,st,z=addr(r["Ship address"] or r["Bill address"])
    bill=sq(r["Bill address"]); ship=sq(r["Ship address"])
    if ship and bill and ship.lower()!=bill.lower(): notes.append(f"Billing address: {bill}")
    row={"First Name":first,"Last Name":last,"Company Name":company,"Phone":pri,"Email":em,"Address":a1,"City":city,"State":st,
         "Postal Code":z,"Tags":"existing customer, quickbooks import","Source":"QuickBooks import","Notes":" | ".join(notes),
         "Additional Phones":", ".join(others),"Additional Emails":", ".join(e for e in ems[1:] if e!=em),"_line":i,"_qb":cust}
    f=flags[i]
    if "test" in (cust+full).lower(): f.append("SKIP test row")
    if not pri and not em: f.append("SKIP no phone and no e-mail")
    if r["Phone numbers"] and not valid: f.append(f"invalid phone {sq(r['Phone numbers'])!r}")
    if not pri: f.append("no phone (no SMS)")
    if not em: f.append("no e-mail")
    if OWN and em.endswith(OWN): f.append("SKIP business's own e-mail")
    if company and re.search(r"pool",company,re.I): f.append("another pool company (B2B)"); row["Tags"]+=", b2b pool company"
    if not last and not company: f.append("one-word name")
    if a1 and not city: f.append("city not recognized")
    if not a1: f.append("no address")
    if "&" in name or " and " in name.lower(): f.append("couple (one contact)")
    if any(x.startswith("SKIP") for x in f): continue
    dup=next((seen[k] for k in (pri,em) if k and k in seen),None)
    if dup is not None:
        base=dup; prop=(cust.partition(":")[0]+" — " if cust.partition(":")[0].lower()!=base["_qb"].partition(":")[0].lower() else "")+(", ".join(x for x in (a1,city,st,z) if x) or cust)
        base["_props"].append(prop)
        f.append(f"same {'phone' if pri and pri==base['Phone'] else 'e-mail'} as line {base['_line']} → merged into that contact (address in its notes)")
        for k in (pri,em):
            if k: seen.setdefault(k,base)
        continue
    row["_props"]=[]
    for k in (pri,em):
        if k: seen.setdefault(k,row)
    outrows.append(row)
for row in outrows:
    if row["_props"]:
        row["Notes"]=" | ".join(x for x in [row["Notes"], "Other QuickBooks entries (same phone/e-mail): " + "; ".join(dict.fromkeys(row["_props"]))] if x)
cols=["First Name","Last Name","Company Name","Phone","Email","Address","City","State","Postal Code","Tags","Notes","Additional Phones","Additional Emails","Source"]
with open(out,"w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(outrows)
with open(review,"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["Line","QuickBooks name","Issue"])
    for i in sorted(flags):
        if flags[i]: w.writerow([i, sq(data[i-4]["Customer full name"]), "; ".join(flags[i])])
c=collections.Counter(x.split(" (")[0].split(" '")[0].split(" as line")[0] for v in flags.values() for x in v)
print("rows",len(data),"import",len(outrows)); print(c.most_common())
