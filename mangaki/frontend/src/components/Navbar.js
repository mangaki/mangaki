import React from 'react'

export default class Navbar extends React.Component {
  static propTypes = {
    children: React.PropTypes.oneOfType([
      React.PropTypes.node,
      React.PropTypes.arrayOf(React.PropTypes.node)
    ]).isRequired
  }

  renderBrand () {
    return (
      <a className='navbar-brand'>
        <img src={require('static/img/minilogo.png')} />
      </a>
    )
  }

  renderHamburgerButton () {
    return (
      <button
        type='button'
        className='navbar-toggle collapsed'
        data-toggle='collapse'
        data-target='#menu-collapse'
      >
        <span className='sr-only'>Ouvrir le menu</span>
        <span className='icon-bar'></span>
        <span className='icon-bar'></span>
        <span className='icon-bar'></span>
      </button>
    )
  }

  renderHeader () {
    return (
      <div className='navbar-header'>
        {this.renderHamburgerButton()}
        {this.renderBrand()}
      </div>
    )
  }

  renderItems () {
    const {children} = this.props

    return (
      <div className='collapse navbar-collapse' id='menu-collapse'>
        {children}
      </div>
    )
  }

  render () {
    return (
      <header className='navbar navbar-default navbar-fixed-top'>
        <nav className='navbar navbar-default' role='navigation'>
          <div className='container-fluid'>
            {this.renderHeader()}
            {this.renderItems()}
          </div>
        </nav>
      </header>
    )
  }
}

export default Navbar
