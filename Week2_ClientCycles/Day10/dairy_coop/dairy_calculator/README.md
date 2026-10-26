# Dairy Co-op Payment Calculator

A small program for the co-op office computer. A farmer types their name and the litres they supplied, and sees the total the co-op owes them at this week's buying price. No more calling 30 farmers every week to pass on the price.

**Version 1.0** (git tag `dairy-calculator-v1.0`). Built for a Kiambu dairy co-op, Week 2 · Day 10.

## What you need

- A computer (Windows, Mac or Linux) with **Python 3.8 or newer**. On Windows, get it from [python.org/downloads](https://www.python.org/downloads/) and tick **"Add Python to PATH"** during install.
- Nothing else. The program uses only what comes with Python.

## Setup

1. Copy this folder (`dairy_calculator`) onto the computer, for example to the Desktop.
2. Open `price.txt` and check that it holds this week's price per litre. It should be **just the number**:
   ```
   55.0
   ```

## Using it

Open a terminal (on Windows: **Command Prompt**) in the folder and run:

```bash
python dairy_calculator.py
```

Type the farmer's name, press Enter, then type the litres and press Enter. The total shows straight away. Press **Enter** for the next farmer, or type **q** to quit.

## Updating the price each week (manager)

1. Open `price.txt` in Notepad (or any text editor).
2. Replace the number with the new price, for example `58` or `57.50`. Just the number, no "KES".
3. Save and close.

That's it. The next time the calculator opens, it shows the new price and the date it was set. If the price is more than 7 days old, the calculator shows a reminder to check it.

## Example

From a real run with the price at KES 55.00:

```
Kiambu Dairy Co-op Payment Calculator
-------------------------------------
Current buying price: KES 55.00 per litre (set Mon 26 Oct 2026)

Farmer name: Jane Wanjiku
Litres supplied: 20

  Farmer : Jane Wanjiku
  Litres : 20
  Price  : KES 55.00 per litre
  Total  : KES 1,100.00

Press Enter for the next farmer, or type q to quit:

Farmer name: Peter Kamau
Litres supplied: twenty
  Please type the litres as a number above 0, e.g. 20 or 12.5
Litres supplied: 32.5

  Farmer : Peter Kamau
  Litres : 32.5
  Price  : KES 55.00 per litre
  Total  : KES 1,787.50

Press Enter for the next farmer, or type q to quit:

Farmer name: Mary Njeri
Litres supplied: 1,250

  Farmer : Mary Njeri
  Litres : 1,250
  Price  : KES 55.00 per litre
  Total  : KES 68,750.00

Press Enter for the next farmer, or type q to quit: q
Goodbye.
```

## When something goes wrong

| What happened | What you see |
|---|---|
| Name left empty | `Please type the farmer's name.` and it asks again |
| Letters, `0` or a negative number for litres | `Please type the litres as a number above 0, e.g. 20 or 12.5` and it asks again |
| `price.txt` is missing | `Can't find price.txt. Create it next to the tool with just this week's price per litre in it, e.g. 55` |
| `price.txt` has words in it | `price.txt should contain just the price per litre, e.g. 55, but it says: 'fifty five'` |
| Price set more than 7 days ago | `Note: the price was set 10 days ago. Check with the manager that it's still this week's price.` |
| Window closed or Ctrl+C | It says `Goodbye.` and closes, with no error screen |

**Why it won't guess a price.** If `price.txt` is missing or wrong, the calculator stops rather than using an old default. Showing 30 farmers the wrong amount would cost more trust than a message saying "fix the price file".

## Good to know

- **Litres can be typed** as `20`, `12.5` or `1,250`.
- **Money is worked out to the cent** and rounded the way you would by hand (half a cent goes up).
- **The litres are for whatever period you're paying** (a day or a week). The tool multiplies by the current price either way.
- **It doesn't save anything.** Each result is shown on screen only. Keeping a payment history isn't part of version 1.0.

## Files

| File | What it is |
|---|---|
| `dairy_calculator.py` | The calculator |
| `price.txt` | This week's price per litre. The only file the manager edits |
| `README.md` | This guide |
