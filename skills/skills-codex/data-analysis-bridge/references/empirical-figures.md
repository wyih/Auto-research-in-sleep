# Empirical research figures

Use R/ggplot2, Stata's graph system, or Python/matplotlib according to the existing project. Build from the source observations or saved estimates and preserve the transformation code.

- State axes, units, sample, time window, and consequential transformations. Comparable panels use consistent scales unless a labeled difference serves the comparison.
- Event/coefficient plots retain the reference category, zero line, event marker, estimates, and interval convention. Show support or changing samples when it affects interpretation; visually distinguish a normalized zero from an estimate.
- Retain a source table of plotted estimates when useful for the paper's downstream writing or packaging. A rendered chart's pixels are insufficient for exact coefficient recovery.
- Use labels and line styles legible in grayscale and at the intended publication/presentation size. Export PDF/SVG for vector exhibits and sufficiently resolved PNG when the consumer requires raster output.
- Inspect the final export for clipped labels, incorrect scales, mismatched legends, and uncertainty hidden by the chosen range. Keep manuscript and slide versions separate when adapting an exhibit.

Completion means the requested figure is reproducible and its displayed values and interpretation agree with the source output. New statistical analyses are needed only when the requested figure depends on them.

Adaptation credits: [Barrios sources](../../shared-references/business-source-attribution.md).
