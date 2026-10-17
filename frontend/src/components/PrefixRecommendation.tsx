import { SolveResult } from "../types";

/**
 * Smallest single block that fits the whole VLSM plan. Shown at the very end of
 * the grading results, after the per-subnet detail, because it summarises the
 * plan rather than any one check.
 */
export function PrefixRecommendation({ solve }: { solve: SolveResult }) {
  if (solve.recommended_prefix == null) return null;

  const size = solve.recommended_block_size ?? 0;
  const addressWord = size === 1 ? "address" : "addresses";

  return (
    <section className="block recommendation" aria-label="Recommended prefix">
      <div className="block-head">
        <div>
          <div className="block-title">Recommended prefix</div>
          <p className="block-sub">
            The smallest single block that holds every address this VLSM plan allocates.
          </p>
        </div>
      </div>
      <div className="recommendation-body">
        <div className="recommendation-prefix mono">/{solve.recommended_prefix}</div>
        <div className="recommendation-facts">
          <div className="fact">
            <span className="fact-k">Fits in one block of</span>
            <span className="fact-v mono">
              {size.toLocaleString()} {addressWord}
            </span>
          </div>
          <div className="fact">
            <span className="fact-k">Addresses allocated</span>
            <span className="fact-v mono">
              {solve.total_addresses_used.toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
