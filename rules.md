# Application Domain Rules

This document is the source of truth for your TDD loop. Fill in each section **before** you write any code — every rule you write here becomes at least one test.

There are no wrong answers, but there are inconsistent ones. Once you decide a rule, your code has to match it.

---

## 1. Currency Symbol

*What currency does your application use, and how is money formatted when it's displayed?*

> _Your answer: $

---

## 2. Standard Categories

*Which expense categories are allowed? Limit yourself to 3–5. What happens if someone uses a category that isn't on your list?*

> _Your answer: Food, Transport, Utilities

---

## 3. Overspending Behaviour (Total Balance)

*What happens when an expense is larger than the total balance? Does your app allow the balance to go negative, or does it block the transaction? If it blocks, what does the caller get back?*

> _Your answer: Block the transaction with an error.

---

## 4. Budget Limits (Category Budgets)

*What happens when an expense exceeds a category's budget limit, but the balance could still cover it? Is it blocked, or is it recorded with a warning?*

> _Your answer: It will be blocked.

---

## TDD Blueprint

Now turn each rule above into the test you will write **before** the implementation exists. Name the behaviour you'd assert.

- [ ] Rule 1 (Currency) → To use dollars as the currency and will have the symbol $.
- [ ] Rule 2 (Categories) → Have three categories: Food, Transport and Utilities
- [ ] Rule 3 (Overspending) → Block any overspending
- [ ] Rule 4 (Budget Limits) → Block any expense that exceeds a category's budget limit.
