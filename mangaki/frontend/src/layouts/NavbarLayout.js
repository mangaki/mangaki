import React from 'react'

import { Link } from 'react-router'
import Navbar from 'components/Navbar'
import NavbarItem from 'components/NavbarItem'

export default class NavbarLayout extends React.Component {
  render () {
    return (
      <Navbar>
        <ul className='nav navbar-nav'>
          <NavbarItem>
            <Link to='/about'>C'est quoi ?</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to='/anime'>Anime</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to='/manga'>Manga</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to='/events'>Calendrier</Link>
          </NavbarItem>
          <NavbarItem>
            <Link to='/top/directors'>Top 20</Link>
          </NavbarItem>
        </ul>
        <ul className='nav navbar-nav navbar-right'>
          <NavbarItem>
            <Link to='/user/login'>
              <span className='glyphicon glyphicon-log-in'></span>&nbsp;Connexion
            </Link>
          </NavbarItem>
        </ul>
      </Navbar>
    )
  }
}
