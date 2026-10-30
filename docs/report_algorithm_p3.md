# Algorithm 1 (Person 3): Trajectory normalization and feature extraction

Checked against the real code (`p3` 1.2.1). Every line matches a step the pipeline performs.

## 1. Preamble (add only if missing)

```latex
\usepackage{algorithm}
\usepackage{algpseudocode}
\renewcommand{\algorithmicrequire}{\textbf{Input:}}
\renewcommand{\algorithmicensure}{\textbf{Output:}}
```

The two `\renewcommand` lines are optional. They print "Input/Output" instead of "Require/Ensure".

## 2. Algorithm (paste at the end of subsection F.1)

```latex
\begin{algorithm}[t]
\caption{Trajectory normalization and structural feature extraction}
\label{alg:p3_normalization}
\begin{algorithmic}[1]
\Require trajectory file $\mathcal{T}$; tool map $\varphi$ (69 tools); tool signatures $\Sigma$; frozen schema $\Phi$
\Ensure normalized trajectories $\mathcal{N}$; feature table $F$
\State stop if the feature code differs from $\Phi$; $\mathcal{N} \gets \emptyset$; $F \gets \emptyset$
\ForAll{records $r \in \mathcal{T}$}
    \State \textbf{if} $r$ is unreadable or its ID is invalid or repeated \textbf{then} log an issue; \textbf{continue}
    \State $E \gets$ events of $r$ in index order, without runner, system and reasoning events
    \State link results to calls; rename call IDs to $c_0, c_1, \dots$; merge a duplicated final answer; recount steps
    \ForAll{tool calls $e \in E$}
        \State $e \gets \bigl(\varphi(e.\mathit{tool}),$ argument types, missing/extra keys vs.\ $\Sigma\bigr)$ \Comment{unknown tool: verb prefix}
    \EndFor
    \State keep whitelisted structural fields only; $\mathcal{N} \gets \mathcal{N} \cup \{E\}$
    \State \textbf{if} no error for $r$ \textbf{then} $F \gets F \cup \{(r.\mathit{id}, \textsc{Features}(E))\}$ \Comment{77 features}
\EndFor
\State \textbf{assert} every \texttt{trajectory\_id} is unique and has one feature row
\State \Return $\mathcal{N}, F$
\end{algorithmic}
\end{algorithm}
```

## 3. Sentence that refers to it (first paragraph of F.1)

```latex
Algorithm~\ref{alg:p3_normalization} summarizes the whole procedure.
```

## 4. Prompt for the AI that edits Overleaf

Attach this file and paste the current LaTeX of the paper below the prompt.

```text
I'm attaching report_algorithm_p3.md. It contains Algorithm 1 for the Person 3 part (trajectory normalization and feature extraction) of our IEEE-style paper. Below it I pasted the current LaTeX of the paper from Overleaf. My teammates' text is final: do not edit, delete or reword any of it.

1. Tell me exactly where to paste Algorithm 1: at the end of the subsection about trajectory processing / normalization (Section III-F, or the Person 3 implementation subsection if it exists). Name the nearest heading and the first words of the paragraph before it.
2. Tell me where to put the sentence "Algorithm~\ref{alg:p3_normalization} summarizes the whole procedure." (first paragraph of that subsection).
3. Check the preamble:
   - Tell me which lines from section 1 of the file are missing and must be added.
   - If the draft already uses another algorithm package (for example algorithm2e or algorithmic), do not add a second one; rewrite Algorithm 1 for that package instead.
   - If \label{alg:p3_normalization} clashes with an existing label, rename mine.
4. Keep every step and its wording exactly as written. Only change LaTeX syntax if it is needed to compile.
5. Make sure it compiles in a two-column IEEEtran document:
   - The algorithm should fit in one column.
   - If a line is too wide, shorten only the \Comment text and tell me what you changed.
6. Output: the final LaTeX blocks to paste, each in its own code block, with one line before each saying where it goes.
```
