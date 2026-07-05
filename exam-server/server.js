const app = require('./app');
const PORT = process.env.PORT || 3000;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || 'xiaomi2026';

app.listen(PORT, () => {
  console.log(`考试服务器已启动: http://localhost:${PORT}`);
  console.log(`管理后台: http://localhost:${PORT}/admin?token=${ADMIN_TOKEN}`);
});
