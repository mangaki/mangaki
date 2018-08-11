Vue.component('bs-light-switch', {
  template: '<label class="switch-light" onclick="">\n' +
  '<input type="checkbox" v-bind:checked="value" v-on:change="updateValue($event.target.checked)">\n' +
  '<slot></slot>\n' +
  '<span class="alert alert-light">\n' +
  ' <span>Off</span>\n' +
  ' <span>On</span>\n' +
  ' <a class="btn btn-primary"></a>\n' +
  '</span>' +
  '</label>',
  props: ['value'],
  methods: {
    updateValue: function (newValue) {
      this.$emit('input', newValue);
    }
  }
});

Vue.component('modal', {
  template: '<transition name="modal">\n' +
  '<div class="modal-mask">\n' +
  '<div role="dialog" aria-labelledby="modalTitle" aria-describedby="modalBody"' +
  'class="modal-wrapper">\n' +
    '<div class="modal-container">\n' +
    '<header id="modalTitle" class="modal-header">\n' +
    '<slot name="header"></slot>\n' +
    '</header>\n' +
    '<section id="modalBody" class="modal-body">\n' +
      '<slot name="body"></slot>\n' +
    '</section>\n' +
    '<footer class="modal-footer">\n' +
      '<slot name="footer"></slot>\n' +
    '</footer>\n' +
    '</div>\n' +
  '</div>\n</div>\n</transition>',
});

$(document).ready(function () {
  window.ProfileSettingsApp = new Vue({
    el: $('#profile_settings_container')[0],
    data: {
      isShared: window.INITIAL_DATA.isShared,
      acceptsNSFW: window.INITIAL_DATA.acceptsNSFW,
      acceptsResearchUsage: window.INITIAL_DATA.acceptsResearchUsage,
      receivesNewsletter: window.INITIAL_DATA.receivesNewsletter,
      enableKbShortcuts: window.INITIAL_DATA.enableKbShortcuts,
      extRatingPolicy: window.INITIAL_DATA.extRatingPolicy,
      convertingExternalRatings: window.INITIAL_DATA.convertingExternalRatings,
      deleteAccountModal: false
    },
    beforeUpdate: function () {
      this.updateProfile();
    },
    methods: {
      convertExtRatings: function () {
        this.convertingExternalRatings = true;
        betterFetch(Urls['api-convert-external-ratings'](), {
          method: 'POST',
          credentials: 'same-origin'
        }).then(resp => {
          if (resp.ok) {
            this.convertingExternalRatings = false;
          } else {
            return Promise.reject(Error(resp))
          }
        }).catch(err => {
          this.convertingExternalRatings = false;
          console.log('Error while converting ratings', err);
        });
      },
      deleteAccount: function () {
        this.deleteAccountModal = false;
        betterFetch(Urls['api-delete-my-account'](), {
          method: 'DELETE',
          credentials: 'same-origin'
        }).then(resp => {
          if (resp.ok) {
            window.location.href = Urls['deleted-account']();
          } else {
            return Promise.reject(Error(resp))
          }
        }).catch(err => {
          // FIXME: we should report back to the frontend.
          console.log('Error while deleting', err);
        })
      },
      exportData: function () {
        betterFetch(Urls['api-export-my-data'](), {
          method: 'POST',
          credentials: 'same-origin'
        }).then(resp => {
          if (resp.ok) {
            return resp.blob();
          } else {
            return Promise.reject(Error(resp))
          }
        }).then(blob => {
          let fakeLink = document.createElement('a');
          document.body.appendChild(fakeLink);
          let targetUrl = window.URL.createObjectURL(blob);
          fakeLink.href = targetUrl;
          fakeLink.download = 'user_archive.zip';
          fakeLink.click();
          window.URL.revokeObjectURL(targetUrl);
          document.body.removeChild(fakeLink);
        }).catch(resp => {
          if (resp.status === 503) {
            /** We should report back to frontend this error **/
            console.log('Could not prepare archive, service unavailable.', resp)
          } else {
            console.log('Unknown error during archive export.', resp);
          }
        });
      },
      updateProfile: function () {
        const payload = {
          is_shared: this.isShared,
          nsfw_ok: this.acceptsNSFW,
          research_ok: this.acceptsResearchUsage,
          newsletter_ok: this.receivesNewsletter,
          keyboard_shortcuts_enabled: this.enableKbShortcuts,
          policy: this.extRatingPolicy
        };
        betterFetch(Urls['api-update-my-profile'](), {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        }).then(resp => {
          return resp.json();
        }).then(data => {
          Object.getOwnPropertyNames(data).map(key => {
            this[key] = data[key];
          });
        }).catch(err => {
          console.log(err)
        });
      }
    }
  })
});
