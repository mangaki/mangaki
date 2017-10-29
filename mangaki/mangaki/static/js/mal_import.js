const IMPORT_PROGRESS_POLLING_FREQUENCY = 1000;

Vue.component('loading-spinner', {
  template: '<div class="sk-circle">\n' +
  '<div class="sk-circle1 sk-child"></div>\n' +
  '<div class="sk-circle2 sk-child"></div>\n' +
  '<div class="sk-circle3 sk-child"></div>\n' +
  '<div class="sk-circle4 sk-child"></div>\n' +
  '<div class="sk-circle5 sk-child"></div>\n' +
  '<div class="sk-circle6 sk-child"></div>\n' +
  '<div class="sk-circle7 sk-child"></div>\n' +
  '<div class="sk-circle8 sk-child"></div>\n' +
  '<div class="sk-circle9 sk-child"></div>\n' +
  '<div class="sk-circle10 sk-child"></div>\n' +
  '<div class="sk-circle11 sk-child"></div>\n' +
  '<div class="sk-circle12 sk-child"></div>\n' +
  '</div>'
});

$(document).ready(function () {
  window.MALImporterApp = new Vue({
    el: $('#mal_container')[0],
    data: {
      followProgress: false,
      showForm: true,
      importFinished: false,
      errorMessage: null,
      serverSideTaskId: null,
      pollingTimer: null,
      currentWorkTitle: null,
      currentWorkIndex: null,
      workCount: null,
      mal_username: ''
    },
    watch: {
      followProgress: function (progressState) {
        if (progressState && !this.pollingTimer) {
          this.startPollingProgress();
        } else if (!progressState && this.pollingTimer) {
          clearInterval(this.pollingTimer);
          this.pollingTimer = null;
        }
      }
    },
    methods: {
      reloadPage: function () {
        location.reload();
      },
      fetchServerSideTaskId: function () {
        return fetch(Urls['api-get-user-tasks'](), {
          credentials: 'same-origin'
        }).then(resp => {
          if (resp.ok) {
            return resp.json();
          } else {
            return Promise.reject(resp);
          }
        }).then(data => {
            console.log(data);
            const malImports = data.filter(item => item.tag === 'MAL_IMPORT');
            if (malImports.length === 0) {
              console.log('No MAL import in progress.');
            } else {
              this.serverSideTaskId = malImports[0].task_id;
              this.followProgress = true;
            }
        }).catch(resp => {
          console.log('Error while fetching user tasks', resp.statusText, resp.status, resp);
        });
      },
      performImport: function (mal_username) {
        return betterFetch(Urls['api-mal-import'](mal_username), {
          method: 'POST',
          credentials: 'same-origin'
        })
          .then(resp => {
            if (resp.ok) {
              return resp.json();
            } else {
              return Promise.reject(resp);
            }
          })
          .then(body => {
              this.serverSideTaskId = body.task_id;
              this.showForm = false;
              this.followProgress = true;
          }).catch(error => {
            if (error.status === 403) {
              this.errorMessage = 'Vous ne pouvez pas importer!';
            } else if (error.status === 500) {
              this.errorMessage = 'Le serveur est dans les choux !';
            } else if (error.status === 429) {
              this.errorMessage = 'Vous avez trop d\'imports pour le moment !';
            } else {
              this.errorMessage = error.statusText;
            }
          })
      },
      importMAL: function () {
        if (this.mal_username.length > 0) {
          this.performImport(this.mal_username)
        }
      },
      checkServerSideTaskId: function () {
        if (!this.serverSideTaskId) {
          this.followProgress = false;
          this.errorMessage = "Subitement, votre ticket d'import a disparu!";
        }
      },
      startPollingProgress: function () {
        this.checkServerSideTaskId();
        this.pollingTimer = setInterval(this.poll, IMPORT_PROGRESS_POLLING_FREQUENCY);
      },
      resetProgress: function () {
        this.followProgress = false;
        this.serverSideTaskId = null;
      },
      poll: function () {
        this.checkServerSideTaskId();
        fetch(Urls['api-get-task-status'](this.serverSideTaskId), {
          credentials: 'same-origin'
        })
          .then(resp => {
            if (resp.ok) {
              return resp.json();

            } else {
              return Promise.reject(resp);
            }
          }).then(body => {
          if (body.details && body.details.currentWork && body.details.currentWork.title) {
            this.currentWorkTitle = body.details.currentWork.title;
            this.currentWorkIndex = body.details.currentWork.index;
            this.workCount = body.details.count || null;
          }
        }).catch(error => {
            if (error.status === 404) {
              this.importFinished = true;
              this.resetProgress();
            } else {
              this.errorMessage = error.message;
          }
        });
      }
    }
  });
});
