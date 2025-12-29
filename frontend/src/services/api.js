import axios from 'axios'

// API base URL - change for production
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class API {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 120000, // 2 minutes for outfit generation
    })
  }

  /**
   * Generate outfits from prompt
   * @param {string} prompt - User's outfit prompt
   * @param {number} maxPrice - Optional maximum price
   * @returns {Promise} - Response with generated outfits
   */
  async generateOutfits(prompt, maxPrice = null) {
    try {
      const response = await this.client.post('/outfits/generate', {
        prompt,
        max_price: maxPrice,
      })
      return response.data
    } catch (error) {
      console.error('API Error:', error.response?.data || error.message)
      throw new Error(
        error.response?.data?.error || 
        error.response?.data?.detail || 
        'Failed to generate outfits'
      )
    }
  }

  /**
   * Submit user feedback on outfit
   * @param {string} outfitId - Outfit ID
   * @param {string} action - User action (like/dislike/skip)
   * @param {string} userId - Optional user ID
   * @returns {Promise} - Response
   */
  async submitFeedback(outfitId, action, userId = null) {
    try {
      const response = await this.client.post('/outfits/feedback', {
        outfit_id: outfitId,
        action,
        user_id: userId,
      })
      return response.data
    } catch (error) {
      console.error('Feedback Error:', error.response?.data || error.message)
      // Don't throw - feedback is non-critical
      return { success: false }
    }
  }

  /**
   * Check API health
   * @returns {Promise} - Health status
   */
  async checkHealth() {
    try {
      const response = await this.client.get('/health', {
        baseURL: 'http://localhost:8000', // Health is at root, not /api/v1
      })
      return response.data
    } catch (error) {
      console.error('Health Check Error:', error.message)
      return { status: 'unhealthy' }
    }
  }

  /**
   * Sync products from external APIs
   * @returns {Promise} - Sync result
   */
  async syncProducts() {
    try {
      const response = await this.client.post('/products/sync')
      return response.data
    } catch (error) {
      console.error('Sync Error:', error.response?.data || error.message)
      throw new Error('Failed to sync products')
    }
  }

  /**
   * Get product count
   * @returns {Promise} - Product count
   */
  async getProductCount() {
    try {
      const response = await this.client.get('/products/count')
      return response.data.count
    } catch (error) {
      console.error('Count Error:', error.message)
      return 0
    }
  }
}

// Export singleton instance
const api = new API()
export default api
