# Policy Guard
Lifecycle components to guard and enforce policies (or instructions) in LLM responses.


## Overview
Policy Guards are post-inference components that can be used to guard for and reinforce policies on LLM responses. A policy can be any statement or instruction that describes a constraint on an LLM response. For example: "The response must be in JSON format" or "The response should not include any hyperboles".

A policy guard takes as input an LLM response and a set of policy statements and produces an output depending on its configuration:

- **Detect Guard**: The guard checks whether the LLM response follows the policy and outputs "Yes/No" along with an explanation.
- **Detect+Repair Guard**: The guard detects and repairs any policy violations in the LLM response; it outputs a rewritten and repaired version of the response.

Detect and Repair are LLM-based and follow a specific _strategy_. The middleware components in this repo support the following detect and repair strategies:

#### Detect Strategies
- **Batch**: all input policies are checked in a single LLM inference
- **Single**: input policies are checked one at a time in a series of LLM inferences

#### Repair Strategies
- **Batch**: the response is rewritten once to repair a set of policy violations in a single LLM inference
- **Iterative**: the response is iteratively rewritten by repairing one policy violation in each iteration.
- **Retry**: retry repeatedly attempts to batch repair the response until no more violations are detected or the maximum number of retries has been reached.
- **Best-of-n**: best-of-n samples _n_ batch repairs using temperature and selects the repaired sample with the fewest number of detected violations.
- **MapReduce**: in the map phase, repaired versions of the LLM response are generated independently for each detected policy violation. During the reduce phase all repaired versions are merged into a single repaired version.

Experimentally, _Best-of-N_ yields the strongest results with the best repair rate. _Batch_ is the most cost-effective strategy as it requires only a single LLM inference for repair.

## Architecture
The answer is passed to the output guardrail block to enforce policy guardrails.

<p align="center">
<img src="../../assets/img_policy_guard_architecture.png" width="300">
</p>

## Results
We evaluated policy guards by measuring the increase in the policy compliance rate that can be achieved with Policy Guards over simply adding the policy statements as instructions in the prompt.

We used a derivative of the popular [IFEval](https://huggingface.co/datasets/google/IFEval) dataset, where we treated instructions as policy statements and scaled the number of instructions added to a query up to ten instructions.  We then measured the policy compliance rate as the instruction following (IF) rate without and with policy guards with using various strategies.

<p align="center">
<img src="../../assets/img_policy_guard_results.png" width="400">
</p>

In the above figure baseline refers to only adding the instructions to the prompt and Detect+Repair refers to the Batch repairer above.
The above figure shows the achieved instruction following (IF) rates for the four strategies using Llama 3.1 70B. The IF rate achieved by only adding the instructions to the prompt is shown as the baseline. Detect+Repair in the figure above refers to the Batch repairer.  All repair strategies lead to IF rate improvements over the baseline. Even at two instructions, policy guards lead to small improvements and the benefits generally increase with the number of instructions. Best-of-N policy guards consistently provide the largest improvements, up to 4 percentage points at ten instructions, increasing the IF rate to 0.70 from 0.66. Best-of-N Oracle refers to a version where we used an oracle detector to select the best of the N generated version to illustrate the potential IF rate achievable through Best-of-N policy guards. Even at two instructions, the model is capable of generating repaired responses with an IF rate of 0.89, a 2 percentage point increase. The boost grows as instructions are increased to ten, when the IF rate reaches 0.75, an 8.5 percentage point increase.

Additional results are reported in [1].

## Getting Started
Refer to this [README](https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/altk/pre_response/policy_guard/README.md) for instructions on how to get started with the code.
See an example in action [here](https://github.com/AgentToolkit/agent-lifecycle-toolkit/blob/main/examples/policy_guard_example.ipynb)

## References
[1] Elder, B., et al., "Boosting Instruction Following at Scale," arXiv preprint arXiv: (2025).  https://arxiv.org/abs/2510.14842
