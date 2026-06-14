import DefaultTheme from 'vitepress/theme'
import ArusHome from './components/ArusHome.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('ArusHome', ArusHome)
  },
}
