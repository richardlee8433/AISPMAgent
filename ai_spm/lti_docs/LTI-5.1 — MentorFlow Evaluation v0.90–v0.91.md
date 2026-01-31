**Most AI products don’t fail because the model is weak.**  
**They fail because we can’t explain quality regressions.**

Over the past few days, I finished v0.90 to v0.91 of the evaluation system for MentorFlow, an AI teaching product I’m building.

This work wasn’t about improving demo quality.  
It was about answering a question every AI PM eventually faces:

When the model changes and performance shifts, how do you know why, and whether to roll back?

v0.90 focused on making AI quality measurable.

Instead of relying on accuracy alone, I built:

- A small golden dataset defining what “good teaching answers” look like
    
- A minimal LLM-as-judge for consistent evaluation
    
- A repeatable eval pipeline with run IDs and version tags
    

The key outcome wasn’t the score.  
It was that quality became observable over time.

v0.91 moved from “correct” to “is this good teaching?”

An answer can be correct but incomplete, confusing, or misleading.  
So I introduced a multi-dimensional rubric across correctness, coverage, reasoning, clarity, and safety.

The first run scored 1.0.  
That wasn’t a success. It was a red flag.

After tightening the rubric, the average score dropped to 0.9667.  
That small drop mattered. It meant the system could detect subtle regressions and support real decisions.

Evaluation isn’t about proving your AI is strong.  
It’s about explaining what changed, why it changed, and whether the trade-off is acceptable.

Next up: regression tracking and failure modes.

**Hashtags**  
#AIPM #AIProductManagement #LLMEvals #AIQuality #BuildInPublic #MentorFlow