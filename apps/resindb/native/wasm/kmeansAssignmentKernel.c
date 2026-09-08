typedef signed int int32_t;
typedef unsigned int uint32_t;

__attribute__((export_name("assign_accumulate")))
int assign_accumulate(
    const double *matrix,
    const double *centroids,
    int32_t *assignments,
    double *sums,
    uint32_t *counts,
    int samples,
    int dimensions,
    int clusters
) {
    int changed = 0;
    for (int sample = 0; sample < samples; ++sample) {
        int best_cluster = 0;
        double best_distance = 0.0;
        for (int dimension = 0; dimension < dimensions; ++dimension) {
            const double delta = matrix[sample * dimensions + dimension] - centroids[dimension];
            best_distance += delta * delta;
        }
        for (int cluster = 1; cluster < clusters; ++cluster) {
            double distance = 0.0;
            const int centroid_offset = cluster * dimensions;
            for (int dimension = 0; dimension < dimensions; ++dimension) {
                const double delta = (
                    matrix[sample * dimensions + dimension]
                    - centroids[centroid_offset + dimension]
                );
                distance += delta * delta;
            }
            if (distance < best_distance) {
                best_distance = distance;
                best_cluster = cluster;
            }
        }
        if (assignments[sample] != best_cluster) {
            assignments[sample] = best_cluster;
            changed += 1;
        }
        counts[best_cluster] += 1;
        const int sum_offset = best_cluster * dimensions;
        const int sample_offset = sample * dimensions;
        for (int dimension = 0; dimension < dimensions; ++dimension) {
            sums[sum_offset + dimension] += matrix[sample_offset + dimension];
        }
    }
    return changed;
}
