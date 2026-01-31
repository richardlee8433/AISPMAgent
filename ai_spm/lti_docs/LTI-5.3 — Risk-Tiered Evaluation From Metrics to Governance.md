**Published:** 2026-01-02 (UTC)  
**MentorFlow:** v0.93  
**Role:** Evaluation → Governance 升級節點

🚦 Not all AI failures are equal. So why do we treat them the same?  
  
This week, I shipped MentorFlow Evaluation v0.93.  
  
On the surface, it looks like a small change.  
Under the hood, it changes how release decisions are understood.  
  
Up to now, our evaluation system answered a simple question:  
Can we release this version or not?  
  
That was v0.92.  
  
But anyone who has worked on a real AI product knows the problem with that framing:  
  
regressions are not rare, they are normal.  
The real question is not whether something failed, but:  
Which failures are we willing to accept and which ones we are not?  
From pass/fail to risk acceptability  
  
In v0.93, evaluation stopped being a binary gate  
and became a risk-tiered governance system.  
  
Each evaluation case is now explicitly classified into a risk tier:  
  
🔴 Risk-critical  
Safety, compliance, core behavior  
→ Any regression = NO-GO  
  
🟡 Edge / ambiguous  
Important but non-fatal behaviors  
→ Regression = fix required  
  
🟢 Signal / happy path  
Quality signals and learning indicators  
→ Regression is recorded, but does not block release  
  
This may sound incremental.  
It isn’t.  
  
Why this matters at scale  
  
On small products, binary evaluation feels “good enough”.  
You remember every issue. You argue case by case.  
  
On large AI products, that breaks down fast.  
  
Without risk tiering:  
  
One minor regression can block a whole release  
  
Ten small issues look “worse” than one critical failure  
  
PMs can’t clearly explain why a release was blocked  
  
Teams start distrusting evaluation altogether  
  
With risk-tiered evaluation, you can finally say:  
  
“We rolled back — not because there were many bugs,  
but because a risk-critical behavior regressed.”  
  
Or just as importantly:  
  
“We shipped — not because it was perfect,  
but because the remaining issues were acceptable risks.”  
  
That difference only becomes visible when products grow.  
But once you hit that scale, it’s everything.  
  
What changed in v0.93  
  
Evaluation decisions are now risk-aware  
  
Failures are no longer treated as symmetric  
  
Release decisions are explainable and defensible  
  
Evaluation becomes part of AI governance, not just QA  
  
In short:  
v0.93 is the first version where MentorFlow behaves like a responsible AI product.  
  
Next up:  
v0.94 : evaluation that learns from real failures  
v0.95 : evaluation as a stakeholder-readable governance layer  
  
But this step mattered more than it looks.  
  
Because at scale, the hardest problem isn’t accuracy —  
it’s deciding which risks you’re willing to live with.  
  
[hashtag#AIPM](https://www.linkedin.com/search/results/all/?keywords=%23aipm&origin=HASH_TAG_FROM_FEED) [hashtag#AIProductManagement](https://www.linkedin.com/search/results/all/?keywords=%23aiproductmanagement&origin=HASH_TAG_FROM_FEED) [hashtag#BuildInPublic](https://www.linkedin.com/search/results/all/?keywords=%23buildinpublic&origin=HASH_TAG_FROM_FEED) [hashtag#MentorFlow](https://www.linkedin.com/search/results/all/?keywords=%23mentorflow&origin=HASH_TAG_FROM_FEED) [hashtag#DecisionBasedEvaluation](https://www.linkedin.com/search/results/all/?keywords=%23decisionbasedevaluation&origin=HASH_TAG_FROM_FEED) [hashtag#Governance](https://www.linkedin.com/search/results/all/?keywords=%23governance&origin=HASH_TAG_FROM_FEED)


![[Pasted image 20260102224609.png]]