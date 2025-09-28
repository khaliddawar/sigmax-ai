const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const isDevelopment = process.env.NODE_ENV !== 'production';

module.exports = {
  mode: isDevelopment ? 'development' : 'production',
  devtool: isDevelopment ? 'inline-source-map' : false,
  
  entry: {
    'background/service-worker': './src/background/service-worker.js',
    'content/content-script': './src/content/content-script.js',
    'content/content-script-robust': './src/content/content-script-robust.js',
    'content/content-script-enhanced': './src/content/content-script-enhanced.js',
    'popup/popup': './src/popup/popup.js',
    'options/options': './src/options/options.js',
    'sidebar/sidebar': './src/sidebar/sidebar.js'
  },
  
  output: {
    path: path.resolve(__dirname, '../build'),
    filename: '[name].js',
    clean: true
  },
  
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env']
          }
        }
      },
      {
        test: /\.css$/,
        use: [
          isDevelopment ? 'style-loader' : MiniCssExtractPlugin.loader,
          'css-loader'
        ]
      },
      {
        test: /\.(png|jpg|gif|svg)$/,
        type: 'asset/resource',
        generator: {
          filename: 'assets/images/[name][ext]'
        }
      }
    ]
  },
  
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        { from: 'manifest.json', to: 'manifest.json' },
        { from: 'src/assets/icons', to: 'assets/icons' },
        { from: 'src/assets/styles', to: 'assets/styles' },
        { from: 'src/assets/templates', to: 'assets/templates' }
      ]
    }),
    
    new HtmlWebpackPlugin({
      template: './src/popup/popup.html',
      filename: 'popup/popup.html',
      chunks: ['popup/popup'],
      minify: !isDevelopment
    }),
    
    new HtmlWebpackPlugin({
      template: './src/options/options.html',
      filename: 'options/options.html',
      chunks: ['options/options'],
      minify: !isDevelopment
    }),
    
    new HtmlWebpackPlugin({
      template: './src/sidebar/sidebar.html',
      filename: 'sidebar/sidebar.html',
      chunks: ['sidebar/sidebar'],
      minify: !isDevelopment
    }),
    
    ...(isDevelopment ? [] : [
      new MiniCssExtractPlugin({
        filename: '[name].css'
      })
    ])
  ],
  
  optimization: {
    minimize: !isDevelopment,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          compress: {
            drop_console: !isDevelopment
          }
        }
      }),
      new CssMinimizerPlugin()
    ]
  },
  
  resolve: {
    alias: {
      '@background': path.resolve(__dirname, '../src/background'),
      '@content': path.resolve(__dirname, '../src/content'),
      '@popup': path.resolve(__dirname, '../src/popup'),
      '@options': path.resolve(__dirname, '../src/options'),
      '@sidebar': path.resolve(__dirname, '../src/sidebar'),
      '@shared': path.resolve(__dirname, '../src/shared'),
      '@assets': path.resolve(__dirname, '../src/assets')
    },
    extensions: ['.js', '.json']
  },
  
  watchOptions: {
    ignored: /node_modules/
  },
  
  performance: {
    hints: isDevelopment ? false : 'warning',
    maxEntrypointSize: 512000,
    maxAssetSize: 512000
  }
};