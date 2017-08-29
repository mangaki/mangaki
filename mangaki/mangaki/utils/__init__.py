from .algos.recommendation_algorithm import RecommendationAlgorithm

# Initialize the factory machinery at import-time.
RecommendationAlgorithm.factory.initialize()
