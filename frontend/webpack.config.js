const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const public_path = path.resolve(__dirname, 'public');

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
    }, {
      test: /\.css$/i,
      loader: 'css-loader',
      options: {
        url: false,
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
          target: 'http://localhost:8000',
          pathRewrite: {'^/api' : ''}
        }
      }
  },
  plugins: [
    new CopyPlugin({
      patterns: [{
        from: path.resolve(__dirname, 'node_modules/katex/dist/katex.min.css'),
        to: public_path,
      }, {
        from: path.resolve(__dirname, 'node_modules/katex/dist/fonts/*'),
        to: path.resolve(public_path, 'fonts'),
        flatten: true,
      }],
    }),
  ],
};
