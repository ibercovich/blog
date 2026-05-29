---
layout: post
title: How Terminal Bench Tasks Get Reviewed
author: Ivan Bercovich
date: 2026-05-20T00:00:00.000Z
---

A PR opens. The author looks legit. The instructions are clean. The metadata is filled in. Static checks pass. The LLM rubric green-lights everything. Agent trials show the task is hard, which is what we want.

The pipeline says yes. Two humans still have to read it before it ships.

Because the pipeline can pass a task that's quietly broken in ways the automation can't see. The verifier checking the wrong thing. The instruction misleading agents toward the wrong answer. The reference solution depending on a value nobody could discover. A cheat agent delegating the whole task to the hidden reference. These are real failures we've caught. None of them shows up in the green check marks.

This post walks through how a Terminal Bench task gets reviewed, and what the human side actually catches.

## How a submission becomes a task

Anyone can submit a task. Many submissions come from first-time authors. A benchmark is only as credible as the worst task in it, so the pipeline has to filter without burning reviewer time.

Cheap static checks first. Then an LLM rubric pass. Then real execution. Then agent trials and adversarial cheat trials. Then two independent human reviews. Each layer catches things the previous one can't see.

### The bot does the welcome

When you open a PR, a bot drops in a comment with the file tree, the task metadata, and the full instruction text. That's what the reviewer reads first. The PR gets labeled and queued. The comment refreshes on every push.

The bot also warns when a PR touches more than one task, or files outside the tasks folder. Both quietly disable later automation.

Then three layers of checks run, cheapest first. No human input. All three have to pass before a reviewer is assigned.

### Layer 1: reject the obvious

Cheap shell scripts looking for obvious mistakes. Missing metadata. Relative paths the agent can't resolve. Missing canary strings. Timeouts past the runner limit. Slugs too long. GPU types that don't exist on the trial backend. Dockerfile hygiene.

None of it is subtle. All of it would cost a reviewer time later. Failures show up inline so the author can fix them before review.

### Layer 2: an LLM grades the task. you still have to read it.

An LLM grades the task against a 27-criterion rubric. Verifiability. Difficulty. Anti-cheat robustness. Alignment between instruction and tests. Environment hygiene. Quality of the metadata explanations. Instruction concision. Novelty. And so on. The rubric is in the repo. Criteria get added when reviewers find patterns worth catching automatically.

This pass is a recommendation, not a verdict. The LLM catches a lot. It also confidently asserts things that don't hold up, contradicts the actual files, or hand-waves through criteria it should have failed. A human still has to read the output and check the claims against the files.

### Layer 3: actually run the thing

The third layer runs the task. Build the container. Run the reference solution end-to-end to confirm it passes. Run a do-nothing agent to confirm doing nothing fails. Run a similarity check against the corpus to catch near-duplicates. Optionally, an AI-detection pass over the instruction and solution.

These catch a different class of problem. Reference solutions that no longer run. Verifiers that pass empty submissions. Tasks nearly identical to one already in the benchmark. Usually authorial drift, not authorial mistake, but the kind of bug that would blow up later.

All three layers run in a controlled checkout. CI scripts come from main, only task files come from the PR. Contributors can't substitute their own workflow logic. Most submissions come from forks, so the system has to be safe by construction.

### A human gets the PR

Once all three layers pass, a reviewer gets auto-assigned from the first-pass pool. Whoever has the fewest active review requests gets the next one. They become the Directly Responsible Individual on the PR. Maintainers can rotate them out if they're overloaded or away.

### Trials measure difficulty. Cheat trials test the verifier.

Once a reviewer is requested, two more automated layers fire. An agent trial and a cheat trial. Both gated on the static and rubric layers passing first. No point spending money on trials against a task that isn't ready.

The agent trial measures difficulty. Several frontier agents try the task, multiple trials each. Results come back as a pass-rate matrix per model. Each trial gets a second-pass LLM analysis with a fixed set of questions. Were the instructions sufficient? Did the agent cheat? Did failure align with the author's stated crux? Did a solution fall just short of a threshold? Did the agent refuse on safety grounds? Did it get cut off mid-progress? You see not just how hard the task is, but *why* it's hard.

The cheat trial asks the opposite question. Each agent gets an adversarial prompt that explicitly authorizes circumventing the verifier. The analysis reads the trajectory afterward to decide whether the agent actually bypassed anything. A caught bypass blocks merge until the task is hardened. Passing means the anti-cheat held. Passing with diverse evasion strategies all caught is much stronger evidence than the same exploit being tried three times.

Results come back as a structured PR comment. Pass/fail per trial, with the LLM verdicts collapsed underneath. A reviewer can tell in about a minute whether the task is calibrated and whether anti-cheat is holding.

### Two humans, two independent passes

After the automation, two humans review the task independently.

**First pass.** A reviewer from the broader pool reads the task in a fixed order: instructions, tests, reference solution, environment, metadata. They use the rubric as a checklist. Is this hard for interesting reasons or just tedious? Would the instruction alone let someone else write the same tests? Can an agent cheat? Do the tests verify real behavior or just string-match? Approve, and the PR moves forward.

**Second pass.** Ryan or I take a fresh look. We're the only two with merge rights. This pass is not a rubber stamp. Two independent reviews make taste and judgment compound. The first reviewer misses something, the second catches it. The second pass also calibrates the first-pass pool. If the same issue keeps slipping past, the rubric gets updated to catch it.

If a task was approved at the proposal stage but feels conceptually wrong now, that's a signal to discuss with the team, not reject. The proposal rubric itself may need updating.

### Reviewing a task by hand takes hours, so we ship tooling

That's a lot of material to read before forming an opinion. Three automated layers, two flavors of trials, prior review comments. Reviewing a single task end-to-end takes hours by hand.

So we ship agent-driven reviewer tooling. It gathers all of that material in one place, audits which prior feedback has been addressed and which is still open, runs a structured pass against the rubric and the trial data, and produces a review summary in a standard shape. Issues found, unaddressed prior feedback, questions for the author, proposed difficulty extensions, and a plain-language explainer for non-experts. The reviewer makes decisions about the assembled picture instead of rediscovering it.

### The pipeline as a whole

```
Static Checks ──► Rubric Review ──► Execution Checks ──► Reviewer Assigned ──► Agent + Cheat Trials ──► 1st Review ──► 2nd Review ──► Merge
```

Each step gates the next. Tasks that fail early layers don't burn the budget of later ones. Reviewers never see PRs that haven't cleared the cheap checks. The visible cost is two human approvals per PR. The invisible cost is the long catalog of failure modes the automation handles before a human opens the file.

Reviewers also get authorship credit on the published benchmark, one point per five reviews.

## The stuff only humans catch

The automation catches a lot. But the meat of the review is reading the task files and trial artifacts directly. Here's what that looks like.

### Start with the prior feedback

Before touching the task files, audit whether every piece of prior feedback was addressed or explicitly declined. This includes anyone who commented, not just the previously assigned reviewer.

For each comment, ask one of three questions. Was the change made? Did the author push back with a reason? Or did the conversation just drop?

The third case is what matters. Tasks accumulate review history over weeks. Without an explicit pass over what's still open, suggestions silently fall off the bottom and a new reviewer ends up re-raising what a prior reviewer already raised. Unaddressed items get a named section in the review summary and surface back to the author in the final comment. Nothing previous reviewers caught gets quietly forgotten.

### The instruction is where a lot of problems hide

Read the instruction first. It frames everything, and most task-level problems show up there.

Watch for instructions that read like LLM prompts. Heavy preamble. Lists of "available tools." Restating the goal three different ways. Watch for instructions that prescribe a process instead of describing an outcome. Watch for instructions that quietly leave out the output format the verifier checks.

The most common problem is bloat. Material that doesn't belong in the prompt because it's either discoverable from the environment or misleading. Six patterns to flag:

- Prose that restates what's in a shipped config or data file.
- Verifier thresholds pasted verbatim. Now the agent designs to the numbers instead of the goal.
- Evaluation sections that re-enumerate fields already mandated by the output schema.
- Prompty scaffolding. "Any strategy is allowed," "feel free to use file X." A domain professional doesn't need permission.
- Warnings about edge cases the environment already handles.
- Long stretches of domain narrative. That belongs in the metadata for human reviewers, not in the agent's prompt.

What an instruction earns is anything the agent can't derive on its own. Behavioral constraints not encoded in shipped code, contracts the verifier enforces, the non-discoverable kernel of the evaluation. Everything else can usually go.

Raise these as questions, not as rewrites. "Does this restate the JSON config?" The author knows the task better than the reviewer. The goal is to make them see the instruction the way the agent will.

### Tests are where the unstated contracts live

Recurring failures in the test suite:

- String-matching as a stand-in for behavior. Brittle. Trivially gameable.
- Tests that enforce the reference solution's implementation, not the requested outcome.
- Numeric tolerance bounds with no rationale for the width.
- Stochastic tasks tested with a single trial.
- LLM-as-judge sneaked in without justification.
- Test suites that quietly grew into a second spec beyond what the instruction says.

Also watch for divergence between the test runner the agent sees and the one the verifier uses for grading. Sometimes the acceptance criteria differ slightly. When they do, the agent's local self-checks are misleading.

The hardest thing to catch is a convention that silently shifts along the chain. Instruction to shipped code to reference solution to test. If the test's reference uses a different normalization or coordinate system or encoding than the source the agent was told to adapt, the agent will faithfully follow what it was given and fail. Catching this means reading all four artifacts side by side.

### The environment leaks too often

The container sets the agent's starting state. Nothing more. Check that the test suite and reference solution aren't baked in. Check that test-only or solution-only dependencies aren't pre-installed. Check that anything the agent shouldn't be able to read is genuinely out of reach.

A subtler check. When the task involves a deliberate exploit path (a WAF to bypass, a proxy to defeat, an SSRF to chain), is that path actually mandatory? Sometimes the backend is reachable directly from inside the container, and the strongest trials skip the intended exploit. Intended difficulty diverges from observed. The task isn't measuring what it claims.

### The reference solution should look like what an agent would have to do

Standard failures in the reference solution:

- Solutions that echo a hardcoded answer instead of computing it.
- Solutions that jump straight to the right approach without any of the exploration an agent would have to do.
- Reference code that diverges from the explanation in the metadata.

The worst pattern is what we call a **privileged-information bottleneck**. The reference solution depends on knowing some specific value. A config file path. An internal port number. A magic string. A database table name. Something the author invented and that no signal in the environment ever surfaces. The agent solves every interesting part of the problem and then fails at the last step because it can't guess the value. The task isn't measuring the intended skill anymore. It's measuring whether the agent happens to share the author's mental model of where things live. Demoralizing for the author. Easy to fix once it's named.

### Metadata is the explainer for human reviewers

Metadata isn't for the agent. It's for the next reviewer. Did the author write substantive explanations of why the task is hard, what the solution approach is, and how verification works? Or did they leave them empty and hand-wave?

Difficulty explanations get flagged when they're framed around the agent ("the agent must do X") instead of the task ("the task requires X knowledge"). When they don't say who in the real world would solve this. When the data is synthetic but the author doesn't say so. Generic tags ("hard", "coding") get pushed back to be specific. Slugs that don't describe the task get renamed. Defaults left in from the template are the surest sign the author rushed through this pass.

### Trial artifacts answer why a task failed in the way it did

This is where the deep review goes beyond what the automated layer can see. The CI gives a high-level verdict per trial. Opening the artifacts lets you answer the harder questions. Why did the task fail in the way it did? Is the difficulty signal real or incidental?

A few things to look at consistently.

**Episode count.** How many turns the agent spent. A diagnostic before reading any content. Very low: the agent gave up or hit a fast failure. Very high: it got stuck and burned its budget. In the thousands: it idled in a no-op loop.

**The transition from productive work to stuck work** is usually the most informative point in a failing trial. Find the moment the agent first mentions the winning concept. The right library. The right exploit primitive. The right insight. Then look at what happens next. If the pivot is too late to act on, it's a near-miss timeout, not an analytical failure. If the agent never reaches it, the difficulty is in the discovery. If it reaches it and can't operationalize, the difficulty is elsewhere.

**Terminal state matters as much as agent narration.** Agents narrate what they think happened. The actual terminal output often tells a different story. A hung process. A heredoc continuation prompt the agent didn't realize it was in. A parse error that looked like silence. Separating reasoning failures from tooling failures is one of the most important things a reviewer does. They have completely different implications for the task.

**Timeouts are not a root cause.** A trial that timed out can be in several states. Making real progress. Stuck in a wrong search space. Wedged in a broken shell. Idle-looping. Split them before deciding whether to raise the timeout. A cluster of near-miss timeouts means the timeout is doing the work. A cluster of analytical timeouts means the task is genuinely hard. A cluster of terminal-wedge timeouts means the environment is fragile.

Beyond timeouts, track a wider taxonomy. Agents that pass every test but one. Agents that get the right idea but compute the wrong number from it. Agents that hit an edge case the API contract didn't make clear. Agents that declare success without verifying. Agents that build a partial solution and abandon it with time still on the clock. Agents that refuse on safety grounds on tasks that are legitimate. The point of the taxonomy is to be specific so the fix lands on the right part of the task.

**Compare the passing trial to the failing ones.** Find the pivot in the passing trial: the exact moment it moved from generic exploration to the winning path. Then look at the corresponding moment in failing trials. Did they get there at all? Did they get there and refuse? Did they get there too late? Did they get there and search the wrong place next? Pass vs fail is a poor failure taxonomy. Where did the pivot diverge is much better.

**Cross-trial signals.** When several trials of the same model converge on the exact same approach (same library, same technique, same payload structure), that's evidence the approach is from training data, not derived from first principles. Useful context for difficulty claims. When all agents fail the same test for the same reason, the task itself is probably ambiguous, or the test relies on undocumented behavior. When passing and failing trials use the same approach but only some pass, the task has variance that needs tightening.

**Crux alignment.** Does what actually broke match what the author said would be hard? If the stated crux is one thing but every failing trial fails on something else, the task is hard for the wrong reasons. Either the instruction, the environment, or the difficulty claim has to change.

### Cheat trials test whether the verifier actually holds

The cheat trials ask a different question. Was the verification actually robust to an agent told to circumvent it?

Cheating agents have a distinctive signature. Very few turns, very small code output, reward zero. When a trial fits that shape, go straight to the artifacts. Read what the agent actually wrote. Confirm the verifier blocked it.

The most informative comparison is across cheating attempts. Multiple agents try genuinely different evasion strategies and all caught: anti-cheat is strong. All try the same exploit and all caught: weaker evidence. The verifier may only cover that one vector. Diverse strategies and some succeed: there are holes to close before merge.

A deliberately weak agent-side check is a legitimate design pattern. The decoy gives cheaters false confidence, and the real verifier catches them later. The catch is more robust because cheaters don't realize they have something else to evade.

### Where the difficulty signal goes wrong

The usual difficulty problems still show up at the start of review. Tedium-as-difficulty. Formatting-as-difficulty. Course-project-sized scope. Memorizable problems. Zero-shot solvable problems. After the trial layer runs, you also see a second class: difficulty that's in the wrong place.

The most common version is threshold-driven difficulty. Many failing trials are near-misses. They pass every structural check but miss one quantitative threshold by a small margin. The threshold is doing the work the conceptual challenge is supposed to do. The fix isn't to tighten the threshold further. It's to introduce a new conceptual challenge in the same domain. The benchmark is supposed to test reasoning, not how close an agent can get to an arbitrary number.

The other version is crux mismatch. Agents fail in a place the author didn't predict, and the difficulty claim no longer matches reality. Usually means the instruction is misleading, the environment is fragile, or the author misjudged where the real challenge lives.

### Three principles for writing the review

Reviews follow a consistent shape. Task overview. Rubric alignment. Trial results. Issues found. Unaddressed prior feedback. Questions for the author. Proposed difficulty extensions. Plain-language explainer. Recommendation. Same shape every time, so contributors learn what a review looks like and reviewers can compare PRs without re-deriving structure.

For the issues themselves, three principles keep things productive instead of adversarial.

**Lead with the concrete discrepancy.** Name the place in the file, show the conflict, skip preamble. "The schema says X but the test checks Y" lands faster than three sentences of setup.

**Frame issues as task problems, not agent problems.** "The verifier silently encodes a fit form the instruction never names" is something the author can act on. "Agents keep failing this test" sounds like a complaint about the agents. It implicitly frames agent success as the goal, which is the opposite of what a benchmark wants.

**Pose, don't prescribe.** The author understands the task better than any reviewer. The reviewer's job is to surface the question, not draft the answer. "Does this restate something the agent can already read?" gives the author the agency to fix it well. "Replace lines 12-14 with X" doesn't.

### How to propose a harder version

After the issues list, reviewers propose harder variants of the same task. A harder version of the same realistic problem, not a different one or a more annoying one.

Good extensions: a constraint a real practitioner in that domain faces. Deepening the time or scale axis in a way the domain naturally exposes. Composing with a sister task that shares tooling. A real-world failure mode the current version doesn't exercise.

Bad extensions: tighten an arbitrary threshold. Bolt on unrelated requirements. Add gotchas. Spec ambiguity dressed up as difficulty.

If the task is already well-calibrated, say so and propose nothing. Manufacturing extensions for their own sake is an anti-pattern.

### Translate the task for non-experts

The last thing a review produces is a plain-language explainer for reviewers outside the task's domain. What this task actually asks. Why it's hard. How the solution works. How verification works. A short glossary of the domain terms in play.

The reviewer pool is wide, and the second-pass reviewer in particular often isn't a domain expert in the subfield the task lives in. The explainer lets that reviewer catch design problems the domain expert took for granted, just by translating the task into terms anyone can engage with.

## Nine patterns from real PRs

The patterns above are easier to spot once you've seen them in the wild. Below are nine examples from the ~65 PRs that have cleared two-pass review. Specific enough to be clear, generalized enough to read without knowing the task.

### Anti-cheat: the cheat agent delegates the entire task to the hidden reference

(PR #354, distributed BM25 in Scala.) A reviewer caught the architecture before any agent had tried it. The submission and the hidden reference implementation were compiled into the same JVM, both registered through Java's `ServiceLoader`. A submission could discover the reference at runtime, filter itself out, and delegate every computation to it. Two cheat agents independently found this in under ten minutes, with no knowledge of the algorithm. The fix had to be architectural: separate JVMs or class-loaders so the lookup couldn't cross the boundary. Any verifier that runs agent code and reference code in a shared runtime has to assume the agent can find and use the reference.

### Spec contract: hidden tests reaching into private internals punish the cleanest architecture

(PR #616, write-ahead-log recovery.) The instruction documented the public API of a storage engine and asked the agent to fix concurrency bugs in it. The hidden tests, though, monkey-patched a private attribute (an internal segment manager) to install timing gates. The instruction said nothing about that attribute. The strongest agent in the run rebuilt the engine cleanly to meet the public contract, but exposed the internals under different names. It failed tests it couldn't even enter. The fix is to either expose the hook publicly, or document the internal name as part of the contract. A benchmark that nominally tests the public API can't quietly require a specific internal one. That punishes exactly the agents capable enough to refactor for cleanliness.

### Spec contract: instruction phrasing fights a domain convention

(PR #473, gender wage gap decomposition.) The instruction told the agent to assign predictor variables to interpretive blocks "according to their meaning" and to "append a squared-term suffix for squared variables." The test then refused any submission that squared one specific variable, because econometric convention in this corner of the literature squares one predictor but not the other. Eight of nine trials made the obvious reading and failed.

The instruction was technically consistent with the convention. Its phrasing actively suggested the wrong reading to anyone who didn't already know it. Fix: name the convention, or accept both readings. An instruction that lets the wrong interpretation look more natural than the right one will produce systematic failures, even on technically-defensible tests.

### Privileged information: the agent solves everything except the one value nobody could discover

(PR #173, Airflow CVE reproduction.) The task involved finding a sensitive admin endpoint on a hardened service. The endpoint name wasn't standard. The source file that defined it was stubbed out at startup. URL enumeration would trip an intrusion-detection rule the task graded against. Agents that found the right credentials had nowhere to use them.

Separately and worse: the agent ran as root, and the credentials happened to live in the init process's environment block. Any agent that thought to read environment variables could skip the entire reconnaissance challenge without making a single web request.

The same PR had two opposite problems. One required guessing an unguessable value. The other let the agent bypass the intended challenge through an unrelated environment leak. Both are "the task isn't measuring what it claims," from opposite directions.

### Wrong-place failure: a UI requirement turning a domain task into a frontend task

(PR #265, medical-claims processing.) The instruction said the agent should submit decisions through a workspace web UI. The backend exposed a clean API that stronger agents discovered and used directly. Agents that took the instruction literally ended up failing on React state-management instead of on the actual claims-reasoning the task was about. The task got drastically different difficulty signals depending on whether the agent figured out it could skip the UI.

If the UI is a path to the domain problem, brittleness in the UI shouldn't be the discriminator. Fix: grade through the API, or make the UI robust enough that it isn't the bottleneck.

### Wrong-place failure: a threshold doing the work the conceptual challenge was supposed to do

(PR #336, reassemble a shuffled network.) Eleven of twelve failing trials converged on the same shape. An optimize-and-check loop that drove the loss close to zero but couldn't reach exact match. At the plateau, the agent was a few swaps away from correct. Every swap made the loss worse, so local search got stuck.

The task was meant to test whether the agent could derive the algebraic structure of the problem and place blocks in one shot, instead of optimizing. The failure pattern was so consistent that reviewers wondered whether the task was actually measuring "can you stop optimizing in time" instead of the intended skill. When the same near-miss shape recurs across trials, the threshold is doing the work. The fix isn't to tighten it. It's to find a new conceptual axis in the same domain.

### Oracle weaker than its own instruction

(PR #183, cumulative layout shift.) The instruction said the agent should fix layout shifts "without losing any visible elements, styling, and analytics from the rendered DOM." The reference solution silently dropped a visible promotional banner, changed its styling from a gold gradient to an invisible 3-pixel bar, and dropped a footer offset. The verifier checked only that the DOM elements existed. Not their content, styling, or position. An agent that took the instruction literally would do far more work than needed. An agent that figured out the verifier was shallow could pass with much less.

The author argued the ambiguity was intentional. Multiple legitimate ways to neutralize the offending behavior, and the verifier shouldn't lock the agent into one. That's defensible. But the visual-integrity gate actually enforced exact magnitudes that exist only as side effects of the obfuscated script the agent was supposed to neutralize. A third, more specific contract the instruction never named. A task can say "preserve element presence" or "preserve all visible properties." What it shouldn't do is say one and check the other.

### Cross-trial signal: identical failures across model families indicate the spec is misleading everyone the same way

(PR #320, soundness-bug repair.) Three agents from three different model families produced the same wrong numerical answer on the same hidden test case. Not a near match, the same wrong number. The reviewer pushed back on the author's "agents naturally trip on this" defense:

> Why do you think they all fail in identical ways though? If they failed in different ways that would be normal. If they fail identically it means all the agents think the answer is something else. Why?

Independent failures look like noise. Identical failures look like the spec is sending everyone down the same wrong path. That's a task problem, not an agent problem.

### Meta: the LLM rubric reviewer hallucinating a passing rationale

(PR #473, slug check.) The rubric caps task slugs at three hyphen-separated tokens. The task had five. The LLM-based rubric review counted the tokens correctly and then marked the criterion PASS with the rationale "exactly five tokens (at the limit)." Five is not the limit; three is. The bot's reasoning and its verdict didn't line up. The kind of failure that makes it impossible to fully delegate rubric enforcement. A human has to read what the bot wrote, not just whether it said PASS.

## Case study: the multi-round arms race that ended in isolation

The patterns above are easier to internalize through one task that hit several of them at once. (PR #268, async job runner.) The author submitted what looked like a tight task. The instructions were clean. The metadata was filled in. Static checks and the rubric pass were both green. Agent trials showed the task was hard. Looking good.

Then we ran the cheat trial.

**Round one.** Gemini got reward 1.0 in a few minutes with no actual bug fixes. It appended module-level code to the production source file that pytest imported during test collection. By the time the import happened, pytest's internals were already in `sys.modules`, so the agent could monkey-patch the test reporter to mark every test as passing. The whole verification reported as green.

The author added AST-based source scanning. Reject any submission that imports pytest internals or patches them at the module level.

**Round two.** Gemini got reward 1.0 again. This time it used `atexit.register(lambda: os._exit(0))` to force a clean exit code regardless of what the tests actually did. The AST scanner wasn't looking for atexit, because atexit is a normal Python module that legitimate code uses all the time.

The author added atexit and a few other process-hijacking patterns to the AST scanner.

**Round three.** Gemini got reward 1.0 a third time. This time it reached pytest's internals via `sys.modules["_pytest"]` directly, without importing anything named `_pytest`. The trigger string never appeared as an import in the source. The AST scanner could not, by construction, see this kind of indirection.

At this point everyone involved stepped back. The author and the reviewers had spent three rounds catching up to evasion strategies that kept getting one move ahead. Every text-pattern defense fell to a slightly more obfuscated way of reaching the same in-process state. The fundamental problem wasn't that the scanner needed to be tighter. It was that the verifier was trusting state inside the agent's own process.

The fix that finally held was structural. The verifier no longer trusts the pytest exit code. After pytest exits, a separate process parses the structured test report and checks that the expected test IDs actually ran and passed. The agent's process can corrupt the in-process state all it wants. The verifier reads the artifacts from outside.

The arms race ended.

The lesson generalizes. Detection is the wrong layer for anti-cheat. Isolation is. Any verifier that grades from inside the agent's process is fundamentally vulnerable, because the agent can always reach further into the process than the scanner can predict. Once we stopped asking "what pattern is the agent using," and started asking "what state is the verifier trusting that the agent can write to," the problem became fixable.

## The uncomfortable conclusion

Every layer catches a class of mistake the previous layer can't see. Static checks catch typos and shape. Rubric review catches structural problems in the spec, tests, and environment. Execution catches "does the oracle actually work." Agent trials catch "is this hard for the reasons you said?" Cheat trials catch "is the verification real?" Human review catches taste, novelty, and judgment the automation can't anchor.

The visible cost of a Terminal Bench task is two human approvals. The invisible cost is everything else. The rubric automation, the trial budget, the cheat trials nobody saw the results of because they came back clean, the prior reviewer whose feedback got incorporated three iterations ago, the hours someone spent reading episode trajectories on a task that ended up getting merged or didn't.

A benchmark is only as credible as the worst task in it. That's a sharper claim than it sounds. One task that turns out to be hackable, or measuring something other than what it claims, costs the rest of the corpus more credibility than the bad task ever earned for the benchmark. The review process is the thing that defends that bar.

That's the bar. Most of what defends it is invisible.
