export type DiffRow =
  | { type: "equal"; leftNum: number | null; rightNum: number | null; left: string; right: string }
  | { type: "changed"; leftNum: number; rightNum: number; left: string; right: string }
  | { type: "removed"; leftNum: number; left: string }
  | { type: "added"; rightNum: number; right: string };

export interface WordSegment {
  text: string;
  changed: boolean;
}

export interface WordDiffResult {
  leftSegs: WordSegment[];
  rightSegs: WordSegment[];
}

const TOKEN_RE = /[A-Za-z0-9_]+|\s+|[^\sA-Za-z0-9_]/g;

function tokenize(line: string): string[] {
  return line.match(TOKEN_RE) ?? [];
}

function mergeSegments(segs: WordSegment[], text: string, changed: boolean): void {
  const last = segs[segs.length - 1];
  if (last && last.changed === changed) last.text += text;
  else segs.push({ text, changed });
}

export function computeWordDiff(left: string, right: string): WordDiffResult {
  const a = tokenize(left);
  const b = tokenize(right);
  const n = a.length;
  const m = b.length;

  const dp: Uint32Array[] = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const leftSegs: WordSegment[] = [];
  const rightSegs: WordSegment[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      mergeSegments(leftSegs, a[i], false);
      mergeSegments(rightSegs, b[j], false);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      mergeSegments(leftSegs, a[i], true);
      i++;
    } else {
      mergeSegments(rightSegs, b[j], true);
      j++;
    }
  }
  while (i < n) mergeSegments(leftSegs, a[i++], true);
  while (j < m) mergeSegments(rightSegs, b[j++], true);

  return { leftSegs, rightSegs };
}

type Op = { op: "equal" | "remove" | "add"; text: string };

function lcsOps(a: string[], b: string[]): Op[] {
  const n = a.length;
  const m = b.length;
  const dp: Uint32Array[] = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));

  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const ops: Op[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      ops.push({ op: "equal", text: a[i] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ op: "remove", text: a[i] });
      i++;
    } else {
      ops.push({ op: "add", text: b[j] });
      j++;
    }
  }
  while (i < n) ops.push({ op: "remove", text: a[i++] });
  while (j < m) ops.push({ op: "add", text: b[j++] });
  return ops;
}

export function computeSideBySide(original: string, transformed: string): DiffRow[] {
  const a = original.split("\n");
  const b = transformed.split("\n");
  const ops = lcsOps(a, b);

  const rows: DiffRow[] = [];
  let leftNum = 0;
  let rightNum = 0;

  for (let k = 0; k < ops.length; k++) {
    const { op, text } = ops[k];
    if (op === "equal") {
      leftNum++;
      rightNum++;
      rows.push({ type: "equal", leftNum, rightNum, left: text, right: text });
    } else if (op === "remove") {
      leftNum++;
      if (k + 1 < ops.length && ops[k + 1].op === "add") {
        rightNum++;
        rows.push({
          type: "changed",
          leftNum,
          rightNum,
          left: text,
          right: ops[k + 1].text,
        });
        k++;
      } else {
        rows.push({ type: "removed", leftNum, left: text });
      }
    } else {
      rightNum++;
      rows.push({ type: "added", rightNum, right: text });
    }
  }

  return rows;
}
