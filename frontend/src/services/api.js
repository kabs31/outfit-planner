import axios from 'axios'

// API base URL - uses environment variable in production
// Note: VITE_API_URL should include /api/v1 if needed, localhost doesn't
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class API {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 300000, // 5 minutes for IDM-VTON outfit generation
    })
    
    this.authToken = null
  }

  /**
   * Set the Firebase auth token for authenticated requests
   * @param {string} token - Firebase ID token
   */
  setAuthToken(token) {
    this.authToken = token
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete this.client.defaults.headers.common['Authorization']
    }
  }

  /**
   * Get user's usage stats (browse count, tryon count)
   * @returns {Promise} - Usage stats
   */
  async getUsage() {
    try {
      const response = await this.client.get('/usage')
      return response.data
    } catch (error) {
      console.error('Usage Error:', error.response?.data || error.message)
      return { browse_count: 0, tryon_count: 0, browse_limit: 3, tryon_limit: 1 }
    }
  }

  /**
   * Browse outfits (FAST - no try-on)
   * @param {string} prompt - User's outfit prompt
   * @param {number} maxPrice - Optional maximum price
   * @param {string} store - Store to browse: 'asos', 'amazon'
   * @param {string} gender - 'men' or 'women'
   * @returns {Promise} - Response with outfit combinations (no try-on images)
   */
  async browseOutfits(prompt, maxPrice = null, store = 'asos', gender = 'women') {
    try {
      // Map store to endpoint
      const storeEndpoints = {
        'asos': '/outfits/browse-asos',
        'amazon': '/outfits/browse-amazon',
        'mixed': '/outfits/browse-mixed'
      }
      const endpoint = storeEndpoints[store] || '/outfits/browse-asos'
      
      console.log(`🛍️ Browsing ${store.toUpperCase()} for: ${prompt}`)
      
      const response = await this.client.post(endpoint, {
        prompt,
        max_price: maxPrice,
        gender: gender,
      })
      return response.data
    } catch (error) {
      console.error('API Error:', error.response?.data || error.message)
      throw new Error(
        error.response?.data?.error || 
        error.response?.data?.detail || 
        'Failed to find outfits'
      )
    }
  }

  /**
   * Browse real products from Shein
   * @param {string} prompt - Fashion prompt
   * @param {number} numTops - Number of tops to fetch
   * @param {number} numBottoms - Number of bottoms to fetch
   * @returns {Promise} - Response with tops and bottoms arrays
   */
  async browseShein(prompt, numTops = 5, numBottoms = 5) {
    try {
      const response = await this.client.post('/shein/browse', {
        prompt,
        num_tops: numTops,
        num_bottoms: numBottoms,
      })
      return response.data
    } catch (error) {
      console.error('Shein API Error:', error.response?.data || error.message)
      throw new Error(
        error.response?.data?.error || 
        error.response?.data?.detail || 
        'Failed to browse Shein products'
      )
    }
  }

  /**
   * Upload user photo for virtual try-on
   * @param {File} file - Image file to upload
   * @returns {Promise} - Response with image URL
   */
  async uploadModelImage(file) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await this.client.post('/upload/model-image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data
    } catch (error) {
      console.error('Upload Error:', error.response?.data || error.message)
      throw new Error(
        error.response?.data?.error || 
        error.response?.data?.detail || 
        'Failed to upload image'
      )
    }
  }

  /**
   * Generate virtual try-on for a specific outfit
   * Supports both URL mode and Base64 mode
   * 
   * @param {Object} options - Try-on options
   * @param {string} options.topImageUrl - URL of top garment (optional if base64 provided)
   * @param {string} options.bottomImageUrl - URL of bottom garment (optional if base64 provided)
   * @param {string} options.modelImageUrl - Optional custom model image URL
   * @param {string} options.topImageBase64 - Base64 data of top image (preferred for ASOS)
   * @param {string} options.bottomImageBase64 - Base64 data of bottom image (preferred for ASOS)
   * @returns {Promise} - Response with try-on image
   */
  async generateTryOn({ 
    topImageUrl = null, 
    bottomImageUrl = null, 
    modelImageUrl = null,
    topImageBase64 = null,
    bottomImageBase64 = null 
  }) {
    try {
      const payload = {
        model_image_url: modelImageUrl,
      }
      
      // Prefer base64 if available (works with ASOS)
      if (topImageBase64) {
        payload.top_image_base64 = topImageBase64
      } else if (topImageUrl) {
        payload.top_image_url = topImageUrl
      }
      
      if (bottomImageBase64) {
        payload.bottom_image_base64 = bottomImageBase64
      } else if (bottomImageUrl) {
        payload.bottom_image_url = bottomImageUrl
      }
      
      console.log('📤 Sending try-on request:', {
        hasTopBase64: !!topImageBase64,
        hasBottomBase64: !!bottomImageBase64,
        hasTopUrl: !!topImageUrl,
        hasBottomUrl: !!bottomImageUrl,
        hasModelUrl: !!modelImageUrl
      })
      
      const response = await this.client.post('/outfits/tryon', payload)
      return response.data
    } catch (error) {
      console.error('Try-On Error:', error.response?.data || error.message)
      throw new Error(
        error.response?.data?.error || 
        error.response?.data?.detail || 
        'Failed to generate try-on'
      )
    }
  }

  /**
   * Generate outfits with try-on (SLOW)
   * @param {string} prompt - User's outfit prompt
   * @param {number} maxPrice - Optional maximum price
   * @returns {Promise} - Response with generated outfits including try-on
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
