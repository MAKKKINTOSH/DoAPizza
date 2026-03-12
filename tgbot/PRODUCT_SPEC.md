# Product Spec

## Audience

The bot is for ordinary customers. It must feel easier than talking to an operator, not harder.

Examples of target users:

- older people
- children
- tired workers
- busy office staff
- technical users who still want the shortest path to food

## UX Principles

1. Speak like a calm human operator.
2. Ask only one clear question at a time.
3. Never expose technical terms such as `state`, `field`, `missing`, `NLP`.
4. Accept free text everywhere. Use buttons only when they reduce effort.
5. Show what is already understood so the user feels heard.
6. Do not throw away the whole order because one detail is wrong.
7. If the user already provided a detail, do not ask for it again.
8. If a value is unsupported by business rules, explain it simply and offer the nearest valid options.

## NLP Strategy

The LLM is the primary source of understanding.

- The LLM extracts entities, edits, intent, and natural follow-up questions.
- Algorithmic logic is only a guardrail.
- Guardrails may:
  - normalize structured choices
  - prevent repeated LLM calls after an exact button-style answer
  - fill a missing required question if the LLM failed to ask it
  - validate business constraints such as allowed pizza sizes

## Size Rules

Supported sizes:

- 25 cm
- 30 cm
- 35 cm

If the user asks for an unsupported size:

- do not reject the whole order
- explain that this size is unavailable
- offer the two nearest supported sizes
- recommend the larger one

Example:

`27 см не делаем. Могу предложить 25 см или 30 см. Советую 30 см.`

## Confirmation Rules

Before final confirmation, the bot must show:

- pizzas and modifiers
- delivery or pickup
- address if delivery
- time
- phone
- comment if present

The user must be able to correct the order without starting from scratch.
