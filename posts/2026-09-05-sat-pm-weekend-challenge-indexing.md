# Week 2 · Sat 2026-09-05 · 17:00 · Weekend Challenge: Make a Query Plan Change Its Mind

> Calendar row: W2 Sat PM, 17:00 (CSV row `35:2`). Format: weekend challenge.
> Pillar: System Design Fundamentals. Pass: Foundations, part 2.
> CSV source: github.com/karanpratapsingh/system-design (GitHub API today:
> 45,880 stars, last push 2026-07-08, not archived). Its Indexes chapter is at
> README.md line 1310, with dense and sparse index subsections following.
> Standards: persona-constitution (Laws I-IV, C-08 zero em dashes, Adversarial
> Review) + AGENTS.md human-first article voice.
>
> Committed calendar beats, all three present below: define a scoped build or
> read exercise on database indexing, from first principles, with a visible
> artifact | point to the exact starting resource | ask readers to post their
> artifact and tag it for review.
> Committed CTA: "Bookmark this; you will need it at 3am someday."
>
> **Every command in this post was executed before publication.** The
> exercise uses `sqlite3` from the Python standard library, so it has no
> install step and no service to run. All outputs quoted below are from real
> runs on this machine today, not illustrations. Measured:
> - 500,000 row table, `SELECT count(*) ... WHERE user_id = 4242`
> - before index: plan `SCAN events`, 11.4 ms
> - index build: 140 ms
> - after index: plan `SEARCH events USING COVERING INDEX idx_events_user (user_id=?)`, 0.036 ms, 315x
> - `WHERE user_id + 0 = 4242`: plan reverts to `SCAN events USING COVERING INDEX`
> - `WHERE kind LIKE '%urchase'`: plan `SCAN events`
> - write amplification, 200,000 inserts: 0 indexes 88 ms, 1 index 187 ms
>   (2.13x), 2 indexes 256 ms (2.92x), 4 indexes 479 ms (5.46x)
>
> Week-3 handoff: database indexing is this week's weekend topic and is not
> otherwise covered in week 2. The challenge is deliberately scoped to query
> plans and write cost, and does not attempt B-tree internals.
>
> **Publication-gap remediation (2026-09-04).** The single reference to this
> week's caching material is restated with its mechanism inline, so a reader
> who has seen none of the week's posts can complete the challenge.
>
> Adversarial review record (2026-09-05):
> - Timings are single measurements on one laptop with a warm page cache and
>   are labeled as such. The post asks readers to compare their own plan
>   output, which is deterministic, rather than to match my milliseconds ✓
> - "315x" is reported with its caveat: it compares a full scan against a
>   covering index lookup, which is close to the best case, and the post says
>   so rather than presenting it as typical ✓
> - The dense and sparse index definitions are attributed to the source repo's
>   Indexes chapter and are quoted accurately ✓
> - No claim is made that SQLite's planner behaves identically to Postgres or
>   MySQL. The transferable part is named explicitly as the shape of the
>   question, not the syntax ✓
> - Zero em dashes.

---

**Topic:** A ninety minute exercise that makes a database query planner visibly change strategy, and then makes it refuse to

**Subtitle:** You will produce one screenshot showing SCAN becoming SEARCH, and a second showing an index sitting there unused because of one character in a WHERE clause.

Good evening, and welcome to the part of the week where you stop reading and go and break something small.

We spent five days on caches. A cache is what you reach for when a query is too slow. This weekend, ninety minutes on the thing you should probably have checked first.

Here is the honest version of why this matters. Plenty of caches exist in production because somebody had a slow query, and nobody ever ran `EXPLAIN` on it. The cache made the symptom go away and added a whole new class of problem: a cache key to get wrong, a TTL to tune, an eviction policy to misconfigure, and a stampede to survive. All five of this week's topics are downstream of a query somebody did not look at.

## What you will have at the end

Two pieces of output. That is the whole artifact and it is deliberately small.

1. A query plan that says `SCAN`, and the same query after one `CREATE INDEX`, saying `SEARCH`.
2. A query plan where you have a perfectly good index and the planner refuses to use it, because of something you wrote in the `WHERE` clause.

The second one is the point. Anyone can add an index. The skill worth ninety minutes is recognizing, on sight, the query shapes that make an index inert.

No installation. `sqlite3` ships inside Python.

## Step 1: read for fifteen minutes, then stop

Open the Indexes chapter of `github.com/karanpratapsingh/system-design`. It is short and it is the right level for this.

Two ideas to take from it. The first is the trade, stated plainly: an index buys faster reads at the cost of increased storage and slower writes, because now you have to write the data *and* update the index. The second is the dense versus sparse distinction. A **dense** index has an entry for every row, so lookups are a straight binary search, and it costs more memory and more maintenance on every insert, update and delete. A **sparse** index has entries for only some records, so it is cheaper to maintain and cheaper in memory, and finding a row means a binary search followed by a scan across a page.

Notice that both of those are the same sentence in different clothes: **an index moves work from read time to write time, and how much it moves is a dial.** Hold that thought until step 4, where you get to measure it.

Then close the tab. Reading more will not help you now.

## Step 2: build something big enough to be honest

Half a million rows. Small enough to build in seconds, large enough that a full scan is visibly slower than a lookup.

```python
import sqlite3, random, time

random.seed(42)
con = sqlite3.connect("idx.db")
con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, user_id INTEGER, "
            "kind TEXT, created_at INTEGER)")
kinds = ["click", "view", "purchase", "signup"]
rows = [(i, random.randrange(1, 50_000), random.choice(kinds),
         1_700_000_000 + random.randrange(0, 31_536_000))
        for i in range(1, 500_001)]
con.executemany("INSERT INTO events VALUES (?,?,?,?)", rows)
con.commit()
```

Do not skip to a smaller table. On ten thousand rows everything is fast and you will learn nothing.

## Step 3: watch the planner change its mind

```python
q = "SELECT count(*) FROM events WHERE user_id = 4242"

print("before:", con.execute("EXPLAIN QUERY PLAN " + q).fetchall())
t = time.perf_counter(); con.execute(q).fetchone()
print(f"  {(time.perf_counter()-t)*1000:.1f} ms")

con.execute("CREATE INDEX idx_events_user ON events(user_id)")
con.commit()

print("after: ", con.execute("EXPLAIN QUERY PLAN " + q).fetchall())
t = time.perf_counter(); con.execute(q).fetchone()
print(f"  {(time.perf_counter()-t)*1000:.3f} ms")
```

Mine printed this:

```
before: [(3, 0, 0, 'SCAN events')]
  11.4 ms
after:  [(3, 0, 0, 'SEARCH events USING COVERING INDEX idx_events_user (user_id=?)')]
  0.036 ms
```

**`SCAN` became `SEARCH`.** That word change is the artifact. Every relational database has its own vocabulary for it, sequential scan versus index scan in Postgres, `type: ALL` versus `type: ref` in MySQL, but the question you are asking is identical in all of them.

The timings on my laptop went 11.4 ms to 0.036 ms, about 315 times. Please do not quote that number at anyone. It is one measurement, on one machine, with a warm cache, and it is close to a best case because SQLite answered entirely from the index without touching the table, which is what "COVERING INDEX" means. Your ratio will differ. The plan change will not, and that is the part to screenshot.

## Step 4: measure what the index cost you

Now the half everybody skips. Time 200,000 inserts into a table with zero, one, two and four secondary indexes.

```python
def bench(n_indexes):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, a INTEGER, b INTEGER, "
                "c TEXT, d INTEGER)")
    for i in range(n_indexes):
        con.execute(f"CREATE INDEX ix{i} ON t({'abcd'[i]})")
    random.seed(42)
    rows = [(i, random.randrange(10**6), random.randrange(10**6),
             f"s{random.randrange(10**5)}", random.randrange(10**6))
            for i in range(1, 200_001)]
    t = time.perf_counter()
    con.executemany("INSERT INTO t VALUES (?,?,?,?,?)", rows)
    con.commit()
    return (time.perf_counter() - t) * 1000

for n in (0, 1, 2, 4):
    print(f"{n} indexes: {bench(n):6.0f} ms")
```

Mine:

```
0 indexes:     88 ms
1 indexes:    187 ms   2.13x
2 indexes:    256 ms   2.92x
4 indexes:    479 ms   5.46x
```

Four indexes, five and a half times the write cost. That is the chapter's sentence about slower writes, with a number attached, and it is why "just add an index" is not free advice on a write-heavy table.

## Step 5: the actual challenge, make the index useless

You have `idx_events_user` on `user_id`. Run these two and read the plans.

```python
q2 = "SELECT count(*) FROM events WHERE user_id + 0 = 4242"
q3 = "SELECT count(*) FROM events WHERE kind LIKE '%urchase'"
print(con.execute("EXPLAIN QUERY PLAN " + q2).fetchall())
print(con.execute("EXPLAIN QUERY PLAN " + q3).fetchall())
```

```
[(3, 0, 0, 'SCAN events USING COVERING INDEX idx_events_user')]
[(3, 0, 0, 'SCAN events')]
```

Back to `SCAN`, both times.

The first one is the lesson. `user_id + 0` is arithmetically identical to `user_id`, and semantically identical, and the planner still gives up, because an index is sorted by `user_id` and not by any expression you might wrap around it. Any function on an indexed column does this. `WHERE lower(email) = ...`, `WHERE date(created_at) = ...`, `WHERE CAST(id AS TEXT) = ...`. The index is right there and it cannot help you, because you did not ask a question it is sorted to answer.

The second is the classic: a `LIKE` pattern with a leading wildcard. An index on a string column is sorted by prefix, so `'purch%'` can use it and `'%urchase'` cannot. There is nothing to seek to.

**Your deliverable:** find a third one. Write a query against this table that you expect to use an index, and does not. Some directions worth trying: a two-column index where you filter only on the second column; an `OR` across two different columns; a sort that the index cannot satisfy; comparing a column against a value of a different type.

Post the query and its `EXPLAIN QUERY PLAN` output. One query, one plan, one sentence on why the planner said no.

## Why this belongs at the end of a caching week

Every mechanism we covered this week exists to avoid asking a question. A CDN avoids asking your origin. A cache-aside read avoids asking your database. An eviction policy decides which answers you keep so you can avoid asking again. Stampede protection is about what happens when many people have to ask at once.

An index is the other move. It makes the asking cheap.

Those are not rivals and you will usually want both. But they fail in opposite directions, and it is worth knowing which one you are looking at. A missing index makes one query slow, consistently, for everybody, and it shows up the moment you run `EXPLAIN`. A misconfigured cache makes some requests slow, sometimes, for reasons that depend on what happened to be in memory ten minutes ago, and it shows up in a percentile nobody is watching.

One of those you can find in ninety minutes on a Saturday. The other one is the rest of your career.

Post your artifact and tag it, and I will read them.

Bookmark this. You will need it at 3am someday.

---

*Monday, 09:00: answers to this morning's three questions, and the start of week three.*
