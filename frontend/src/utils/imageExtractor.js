/**
 * Image Extractor Utility
 * Extracts images from URLs using canvas (works with CORS-blocked images in browser)
 */

/**
 * Extract image from URL as base64 data URL
 * @param {string} imageUrl - URL of the image to extract
 * @param {number} timeout - Timeout in milliseconds (default: 15000)
 * @returns {Promise<string>} - Base64 data URL (data:image/png;base64,...)
 */
export async function extractImageAsBase64(imageUrl, timeout = 15000) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous'; // Required for CORS
    
    const timeoutId = setTimeout(() => {
      reject(new Error(`Image load timeout for: ${imageUrl.substring(0, 50)}...`));
    }, timeout);
    
    img.onload = () => {
      clearTimeout(timeoutId);
      
      try {
        // Create canvas
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        
        // Draw image to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        
        // Extract as base64
        const base64Data = canvas.toDataURL('image/png');
        
        console.log(`✅ Extracted image: ${img.naturalWidth}x${img.naturalHeight}`);
        resolve(base64Data);
        
      } catch (error) {
        // Canvas tainted - CORS issue
        console.warn(`⚠️ Canvas extraction failed (CORS): ${error.message}`);
        reject(new Error('CORS_ERROR'));
      }
    };
    
    img.onerror = () => {
      clearTimeout(timeoutId);
      console.error(`❌ Failed to load image: ${imageUrl.substring(0, 50)}...`);
      reject(new Error('IMAGE_LOAD_ERROR'));
    };
    
    // Start loading
    img.src = imageUrl;
  });
}

/**
 * Extract multiple images as base64
 * @param {string[]} imageUrls - Array of image URLs
 * @returns {Promise<{url: string, base64: string | null, error: string | null}[]>}
 */
export async function extractMultipleImages(imageUrls) {
  const results = await Promise.allSettled(
    imageUrls.map(async (url) => {
      try {
        const base64 = await extractImageAsBase64(url);
        return { url, base64, error: null };
      } catch (error) {
        return { url, base64: null, error: error.message };
      }
    })
  );
  
  return results.map((result) => 
    result.status === 'fulfilled' ? result.value : { url: '', base64: null, error: 'Unknown error' }
  );
}

/**
 * Preload an image to ensure it's in browser cache
 * Useful for images that are displayed but need to be extracted later
 * @param {string} imageUrl - URL of image to preload
 * @returns {Promise<boolean>} - True if preloaded successfully
 */
export function preloadImage(imageUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = imageUrl;
  });
}

export default {
  extractImageAsBase64,
  extractMultipleImages,
  preloadImage,
};


