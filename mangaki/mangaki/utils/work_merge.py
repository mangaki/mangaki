from mangaki.models import WorkCluster


def merge_work_clusters(*clusters):
    target_cluster = clusters[0]
    for cluster in clusters[1:]:
        union_work_cluster(target_cluster, list(cluster.works.all()))
        cluster.delete()
    return target_cluster


def union_work_cluster(cluster, works):
    cluster.works.add(*works)


def create_work_cluster(works):
    # Union-Find approach.
    target_cluster = None
    for work in works:
        clusters = list(work.workcluster_set.all())
        if clusters:
            target_cluster = clusters[0]
            break

    if not target_cluster:
        target_cluster = WorkCluster.objects.create()

    union_work_cluster(target_cluster, works)

    return target_cluster
