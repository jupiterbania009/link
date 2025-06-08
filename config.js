const config = {
    API_BASE_URL: process.env.NODE_ENV === 'production' 
        ? 'https://your-render-app-name.onrender.com'  // Replace with your Render URL
        : 'http://localhost:5000'
};

export default config; 