# Finding unfinished parts in assembly

_Created: 2026-09-05T13:36:04.585272Z_
_Updated: 2026-09-05T13:37:58.999928Z_

## Human

lets solve this problem
Tesla is investigating production bottlenecks and they need your help to extract the relevant data. Write a query to determine which parts have begun the assembly process but are not yet finished.
Assumptions:
parts_assembly table contains all parts currently in production, each at varying stages of the assembly process.
An unfinished part is one that lacks a finish_date.
This question is straightforward, so let's approach it with simplicity in both thinking and solution.
Effective April 11th 2023, the problem statement and assumptions were updated to enhance clarity.
parts_assembly Table
Column Name	Type
part	string
finish_date	datetime
assembly_step	integer
parts_assembly Example Input
part	finish_date	assembly_step
battery	01/22/2022 00:00:00	1
battery	02/22/2022 00:00:00	2
battery	03/22/2022 00:00:00	3
bumper	01/22/2022 00:00:00	1
bumper	02/22/2022 00:00:00	2
bumper		3
bumper		4
Example Output
part	assembly_step
bumper	3
bumper	4
Explanation
The bumpers in step 3 and 4 are the only item that remains unfinished as it lacks a recorded finish date.
The dataset you are querying against may have different input & output - this is just an example!

---

## Assistant

Go ahead and share your query or approach for this one — I'll tell you if you're on the right track.

---

## Human

the goal is to find to find which parts begun the assembly process but are not yet finished.
So there finish_date will be null.
Thus, my query will be -
SELECT part,assembly_step FROM parts_assembly
WHERE finish_date IS NULL

---

## Assistant

That's correct and it's already the simplest, most optimal way to write it — a straightforward filter on NULL, no joins or subqueries needed. Nothing to optimize further here.

Since you solved it independently, here's your block:

Parts Assembly — Unfinished Parts — Notion Notes
Type: First Solve
Bucket: Bucket 1 — Fundamentals
Query: SELECT part, assembly_step FROM parts_assembly WHERE finish_date IS NULL
Difficulty: Easy
Notes: Solved without any help.
Revision Needed: Low

---
