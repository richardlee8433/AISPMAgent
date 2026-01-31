My model scored 0.98.  
I still blocked the release.  
  
That wasn’t a bug.  
It was a decision.  
  
In MentorFlow v0.92, we changed what “evaluation” means.  
Most AI evaluation systems still answer one question: “How good is the model?”  
  
But that’s not the question PMs actually need.  
  
The real question is: “Can we trust this behavior enough to release it?”  
  
In our latest evaluation run:  
•Average score: 0.9833  
•15 test cases  
•Almost everything passed  
Yet the final decision was: FIX-REQUIRED (Medium Risk)  
  
Why?  
  
Because one specific case — c1_q04_long_context_tradeoff — showed a coverage gap.  
  
Not a hallucination.  
Not a safety violation.  
Just an incomplete explanation in a long-context tradeoff scenario.  
  
And that was enough to block the release.  
  
What changed in v0.92?  
We stopped treating evaluation as a QA scorecard.  
  
Instead, we introduced decision-based evaluation:  
•Individual cases produce raw signals  
•Signals flow into explicit governance rules  
•The system outputs a release decision, not just metrics  
  
In other words:  
  
Evaluation ≠ QA  
Evaluation = Release decision support  
  
The system is allowed to say:  
  
“I don’t care that the average score is high. This specific behavior still isn’t good enough to ship.”  
  
This is what AI governance looks like in practice.  
  
Not dashboards full of numbers.  
Not post-hoc explanations after things go wrong.  
  
But explicit, auditable decisions made before release.  
  
v0.93 will go further with risk tiering (🔴🟡🟢),  
but v0.92 was the real inflection point: The moment evaluation stopped being descriptive and became actionable.  
  
[hashtag#AIPM](https://www.linkedin.com/search/results/all/?keywords=%23aipm&origin=HASH_TAG_FROM_FEED) [hashtag#AIProductManagement](https://www.linkedin.com/search/results/all/?keywords=%23aiproductmanagement&origin=HASH_TAG_FROM_FEED) [hashtag#BuildInPublic](https://www.linkedin.com/search/results/all/?keywords=%23buildinpublic&origin=HASH_TAG_FROM_FEED) [hashtag#MentorFlow](https://www.linkedin.com/search/results/all/?keywords=%23mentorflow&origin=HASH_TAG_FROM_FEED) [hashtag#DecisionBasedEvaluation](https://www.linkedin.com/search/results/all/?keywords=%23decisionbasedevaluation&origin=HASH_TAG_FROM_FEED)

![[LTI5.2 1.png]]