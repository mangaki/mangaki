import React from 'react'
import classNames from 'classnames'

export default class NavbarItem extends React.Component {
  static propTypes = {
    className: React.PropTypes.string,
    children: React.PropTypes.oneOfType([
      React.PropTypes.node,
      React.PropTypes.arrayOf(React.PropTypes.node)
    ]).isRequired
  }

  render () {
    const {children, className} = this.props
    return (
      <li className={classNames(className)}>
        {children}
      </li>
    )
  }
}
