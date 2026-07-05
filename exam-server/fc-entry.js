const serverless = require('serverless-http');
const app = require('./app');

// 阿里云函数计算 FC HTTP 触发器入口
exports.handler = serverless(app, {
  binary: ['image/*', 'font/*'],
});
