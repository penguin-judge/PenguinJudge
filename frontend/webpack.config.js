const path = require('path');

module.exports = {
  entry: './src/index.ts',
  module: {
    rules: [{
      test: /\.ts$/,
      loader: 'ts-loader',
      exclude: /node_modules/,
      options: {
        configFile: 'tsconfig.json',
      },
    }],
  },
  resolve: {
    extensions: ['.ts', '.js'],
  },
  output: {
    filename: 'bundle.js',
    path: path.join(__dirname, 'dist'),
  },
  devServer: {
    contentBase: path.join(__dirname, 'public'),
      historyApiFallback: true,
      proxy: {
        '/api': {
          target: 'http://localhost:5000',
          pathRewrite: {'^/api' : ''}
        }
      }
  },
};
