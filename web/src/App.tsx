import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import { Empty, Loading } from './components/ui'
import { startSmoothScroll } from './lib/motion'
import { useApp } from './lib/store'

const Overview = lazy(() => import('./pages/Overview'))
const Data = lazy(() => import('./pages/Data'))
const Explore = lazy(() => import('./pages/Explore'))
const Aspects = lazy(() => import('./pages/Aspects'))
const Topics = lazy(() => import('./pages/Topics'))
const Insights = lazy(() => import('./pages/Insights'))
const Model = lazy(() => import('./pages/Model'))
const Method = lazy(() => import('./pages/Method'))

function NotFound() {
  return (
    <div className="wrap" style={{ padding: '100px 0' }}>
      <Empty title="This page does not exist">
        Go back to the <Link to="/">overview</Link>.
      </Empty>
    </div>
  )
}

export default function App() {
  const theme = useApp((s) => s.theme)
  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])
  useEffect(() => startSmoothScroll(), [])
  return (
    <BrowserRouter>
      <Shell>
        <Suspense fallback={<div className="wrap"><Loading what="Loading page" /></div>}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/data" element={<Data />} />
            <Route path="/explore" element={<Explore />} />
            <Route path="/aspects" element={<Aspects />} />
            <Route path="/topics" element={<Topics />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/model" element={<Model />} />
            <Route path="/method" element={<Method />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </Shell>
    </BrowserRouter>
  )
}
