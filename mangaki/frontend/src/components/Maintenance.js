import React from 'react'

export class Maintenance extends React.Component {
    render () {
        return (
                <div className="container">
                    <h1>Désolé !</h1>
                    <p>
                        Mangaki est en maintenance ! En attendant, vous pouvez
                        <a href="http://meta.mangaki.fr">consulter le forum</a>.
                    </p>
                </div>
        )
    }
}
export default Maintenance