import { Component } from 'react'
import { HeroFallback } from './HeroFallback'

// Keep this module independent of the lazy-loaded WebGL dependency graph.
export class HeroErrorBoundary extends Component {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error) {
    console.warn('Hero visualization unavailable; using static background.', error)
  }

  render() {
    return this.state.failed ? <HeroFallback /> : this.props.children
  }
}
