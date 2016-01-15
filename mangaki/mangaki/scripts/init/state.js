/** Load the initial state from Django **/

let globalState = {}
if (window.__INITIAL_STATE__) {
  globalState = window.__INITIAL_STATE__
  if (__DEBUG__) {
    console.log('Loaded initial state from Django', globalState)
  }
} else {
  if (__DEBUG__) {
    console.log('No initial state from Django received')
  }
}

export default globalState
