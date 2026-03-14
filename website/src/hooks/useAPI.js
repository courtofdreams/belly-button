const API_HOST = import.meta.env.VITE_API_HOST || 'http://localhost:8000'

const useAPI = () => {
  const fetchRecommendationsByCoordinates = async (lat, lng, radius = 1000) => {
    try {
      const response = await fetch(
        `${API_HOST}/api/restaurants-recommendation?lat=${lat}&lng=${lng}&radius=${radius}`
      )
      if (!response.ok) {
        throw new Error('Failed to fetch restaurants data')
      }
      return await response.json()
    } catch (error) {
      console.error('Error fetching restaurants data:', error)
      throw error
    }
  }

  return { fetchRecommendationsByCoordinates }
}

export default useAPI
