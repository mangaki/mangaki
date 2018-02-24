"use strict";

function debounce(callback, wait) {
  var timeout;
  return function () {
    var ctx = this, args = arguments;
    var later = function () {
      timeout = null;
      callback.apply(ctx, args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function throttle(callback, threshold) {
  var last, deferTimer;
  return function () {
    var context = this;
    var now = +new Date, args = arguments;

    if (last && now < last + threshold) {
      clearTimeout(deferTimer);
      deferTimer = setTimeout(function () {
        last = now;
        callback.apply(context, args);
      }, threshold);
    } else {
      last = now;
      callback.apply(context, args);
    }
  }
}

$(function () {
  // We need to setup a few things on ratings elements:
  //  - Ensure checkboxes inside a given .ratings are exclusive.
  //  - Send the votes to the server when the checkboxes are checked.
  //  - Ensure tooltips are displayed on hover
  $('.ratings:not(.ratings_other)').each(function () {
    var ratings = this;
    var endpoint = $(ratings).data('endpoint') || '/vote';

    // Make checkboxes exclusive inside this set of ratings.
    var checkboxes = $(ratings).find('.rating__checkbox');
    checkboxes.each(function () {
      $(this).on('change', function () {
        var checkbox = this;

        checkboxes.each(function () {
          if (this !== checkbox && this.checked) {
            this.checked = false;
          }
        });

        var name = this.name, choice = this.value;
        // FIXME: Currently, we are relying on the fact that the checkboxes are
        // named e.g. 'rating[7]' with the ID of the work, and parsing that
        // here. In the future, we should use a form-encoded request with the
        // raw input data directly, and parse it on the server. This would
        // allow the possibility of rating a bunch of works without JS, even
        // though it would be a less agreable user experience than with working
        // JS.
        var work_id = name.substring(name.indexOf('[') + 1, name.indexOf(']'));

        $.post(endpoint + '/' + work_id, {choice: choice}, function (rating) {
          if(rating !== choice) {
            checkboxes.each(function () {
              this.checked = this.value === rating;
            });
          }
        });
      });
    });

    // Setup tooltips on the ratings.
    $(ratings).find('.rating[title]').tooltip({
      'container': 'body',
      'placement': function () {
        return ratings.offsetHeight > ratings.offsetWidth ? 'auto left' : 'auto top';
      },
    });
  });

  /* By registering any kind of touch event, we are implicitely telling Safari
   * on iOS to handle the whole document as a touch surface, which in turns
   * makes it trigger :hover on touch, which is the behavior of all other
   * browsers.
   */
  document.addEventListener('touchstart', function () { });
});

/* A Card is a thin wrapper around an element used to display work cards. It
 * mostly provides a simple API for changing its content through a JSON object,
 * as well as properly managing visual transitions when doing so.
 */
function Card(el, category) {
  this.$el = $(el);
  this.category = category;
  this.work = null;

  return this;
}

/* De-hydrates the card, that is, remove it from view. This uses a fade-out
 * transition.
 *
 * `dehydrate` should only be called on a currently hydrated card.
 *
 * Returns a promise which completes once the card has been removed from view.
 */
Card.prototype.dehydrate = function () {
  return Promise.resolve(this.$el.fadeOut().promise());
};

/* Hydrate the card with a JSON object describing the underlying work. This
 * uses a fade-in transition towards the new card state.
 *
 * `work` can either be undefined (in which case the card will be replaced with
 * the loading Chiro), or an object with the following properties describing
 * the work that should be displayed:
 *  - id
 *  - title
 *  - poster
 *  - synopsis
 *
 * `hydrate` should only be called on a currently dehydrated card.
 *
 * Returns a promise which completes once the transition is complete and the
 * card displays the requested work.
 */
Card.prototype.hydrate = function (work) {
  var $el = this.$el;

  if (typeof work === 'undefined') {
    return Promise.resolve($el.addClass('work-card_loading').fadeIn().promise());
  }

  // FIXME: We should use a solution that doesn't require monkey-patching HTML
  // with jQuery in the future, but for now that is the easiest way.
  $el.find('.work-card__media').css('background-image', 'url("' + work.poster + '")');
  $el.find('.work-card__title').text(work.title);
  $el.find('.work-cover__wrapper').attr('data-category', work.category);
  $el.find('.work-card__synopsis').html(work.synopsis);
  $el.find('.work-card__link').attr('href', '/' + this.category + '/' + work.id);
  $el.find('.ratings .rating__checkbox').attr('name', 'rating[' + work.id + ']').each(function () {
    this.checked = false;
  });

  this.work = work;

  return Promise.resolve($el.removeClass('work-card_loading').fadeIn().promise());
};

/* Wraps a Promise to ensure that it will resolve with the correct animations.
 * This returns a promise with the same result as the given promise, but it
 * guarantees that it will only resolve when the card is dehydrated (hidden)
 * and takes care of properly displaying transitions (including showing the
 * loading screen if needed) while waiting for the promise to resolve.
 *
 * Technically, `parallelLoad` does something similar to the following:
 *
 *  - If the card is currently showing the loading screen, we simply wait for
 *  the promise to resolve, then dehydrate the card and return the promise's
 *  result.
 *  - If the card is currently hydrated with a non-empty work, we first
 *  dehydrate the card, then check whether the promise finished. If that is the
 *  case, we return the promise's result; otherwise we re-hydrate the card with
 *  an empty work (i.e., display the loading screen), wait for the promise to
 *  resolve, then return the promise's result.
 */
Card.prototype.parallelLoad = function (promise) {
  var card = this;
  // Ensure we are actually handling a Promise.
  promise = Promise.resolve(promise);

  if (this.$el.hasClass('work-card_loading')) {
    return promise.then(function (work) {
      return card.dehydrate().then(function () {
        return work;
      });
    });
  }

  // FIXME: We really should use a Symbol here.
  var dehydrate = this.dehydrate().then(function () { return undefined; });

  return Promise.race([dehydrate, promise]).then(function (work) {
    if (typeof work === 'undefined') {
      return Promise.all([promise, card.hydrate()]).then(function (results) {
	var work = results[0];

	return card.dehydrate().then(function () {
	  return work;
	});
      });
    } else {
      return dehydrate.then(function () {
	return work;
      });
    }
  });
};

/* Convenience method to focus the Card DOM element. */
Card.prototype.focus = function () {
  this.$el.focus();
};

/* Vote for this card */
Card.prototype.vote = function (choice) {
  this.$el.find('.rating_' + choice).trigger('click');
  this.focus();
};

var CARD_SHORTCUTS = {
  'e': 'favorite',
  'r': 'like',
  't': 'neutral',
  'y': 'dislike',
  'g': 'willsee',
  'h': 'wontsee'
};

/* Bind shortcuts */
var DEBOUNCE_VOTE_TIME = 250;
Card.prototype.bindShortcuts = function () {
  /* Objective: rating works should be fast.
     Constraints: 6 votes buttons.

     Strategy: use two columns of the keyboard.

     E: Favorite.
     R: Like.
     T: Neutral.
     Y: Dislike.

     G: Will see.
     H: Won't see.

     This way, it's AZERTY/QWERTY independent.
     And permit quick & fast rating when you learn those shortcuts.
   */

  var card = this;
  $.each(CARD_SHORTCUTS, function (keystroke, vote_value) {
    Mousetrap.bind(keystroke, debounce(() => card.vote(vote_value), DEBOUNCE_VOTE_TIME), 'keypress');
  });
};

/* Unbind shortcuts */
Card.prototype.unbindShortcuts = function () {
  $.each(CARD_SHORTCUTS, function (keystroke) {
    Mousetrap.unbind(keystroke);
  });
};

/* A Slot is a cache around an endpoint returning works in JSON format as
 * expected by `Card.hydrate`. It provides a simple, Promise-based API for
 * getting the next cached work as well as requesting additional work objects
 * from the given URL on the server.
 */
function Slot(url) {
  this.url = url;
  this.works = [];

  // Prefetch works
  this.fetch();

  return this;
}

/* Returns additional work objects from the server. The Slot uses internal
 * variables to ensure that there never are two requests from the same Slot to
 * the server, and that any caller that requested a `fetch()` during a single
 * request was in-flight will get their promises resolved.
 *
 * Returns a promise for the slots' new list of works after getting fetched
 * from the server.
 */
Slot.prototype.fetch = function () {
  if (typeof this.fetcher !== 'undefined') {
    return this.fetcher;
  }

  var slot = this, works = this.works;
  return this.fetcher = Promise.resolve($.getJSON(this.url)).catch(function (exn) {
    slot.fetcher = undefined;
    throw exn;
  }).then(function (result) {
    Array.prototype.push.apply(works, result);

    slot.fetcher = undefined;
    return works;
  });
};

function buildSlotURL(category, slot_sort) {
  return '/api/cards/' + category + '/' + slot_sort;
}

/* Mosaic takes care of mapping Cards inside an element with Slots pointing to
 * some remote URLs on the server.
 */
function Mosaic(el, category, enable_shortcut) {
  var mosaic = this;
  this.shortcutsEnabled = enable_shortcut || false;

  // Stores the IDs of works this Mosaic has already displayed, to avoid
  // duplication.
  this.dejaVu = [];

  var els = $(el).find('.work-card').toArray();

  this.slots = els.map(function (el) {
    return new Slot(buildSlotURL(category, el.getAttribute('data-slot-sort')));
  });
  this.cards = els.map(function (el, index) {
    var card = new Card(el, category);

    card.$el.find('.rating__checkbox').on('change', function () {
      // When someone rates a work on the mosaic, we'll give them the next one.
      mosaic.loadCard(index);
    });

    return card;
  });

  // Prepopulate cards. We assume that all the cards start in loading state.
  var loadingPromises = [];
  for (var i = 0, l = this.cards.length; i < l; ++i) {
    loadingPromises.push(this.loadCard(i));
  }

  if (this.shortcutsEnabled) {
    this.currentFocusedCard = null;
    Promise.all(loadingPromises)
      .then(function () {
        mosaic.focusCard(0);
        mosaic.bindGlobalShortcuts();
      });
  }

  return this;
}

/* Finds the next work that should be displayed on one of the cards. Usually,
 * this is simply the next work from the corresponding slot; however, this also
 * takes care of the case where one of the slots is actually empty (both on the
 * local cache and on the server), which can happen on development instances
 * with small databases or if someone has rated all the works in one of the
 * slots with a hard limit on its size (e.g. popular works).
 */
Mosaic.prototype.next = function (index) {
  // This function computes the hydration values that should be used for the
  // next card in the slot at index.
  var dejaVu = this.dejaVu, slots = this.slots;

  var refetch = true;
  var slot = slots[index], i = -1;

  function filterDejaVu(work) {
    if (typeof work === 'undefined') {
      if (refetch) {
        // We allow ourselves one try for re-loading the current slot from the
        // server. If that fails, we'll steal works from the other slots -- but
        // won't try to fetch more works from the server for those, because if
        // we are in a situation where all slots are empty, the user probably
        // has rated almost all available works and querying the server like
        // crazy will only cause a DoS.
        refetch = false;

        return slot.fetch().then(function (works) {
          return works.shift();
        }).then(filterDejaVu);
      }

      // We didn't find anything in the current slot; let's try other slots.
      do { ++i; } while (i === index);

      // Nope, there really is nothing we can do. At least we tried our best.
      if (i >= slots.length) {
        return undefined;
      }

      slot = slots[i];
      return filterDejaVu(slot.works.shift());
    }

    // Can't reuse a work the user has already seen.
    if (dejaVu.indexOf(work.id) !== -1) {
      return filterDejaVu(slot.works.shift());
    }

    dejaVu.push(work.id);
    return work;
  }

  return Promise.resolve(filterDejaVu(slot.works.shift())).then(function (work) {
    if (typeof work === 'undefined') {
      return work;
    }

    // We first load the Image object in JavaScript in order to only display
    // the cards once the images are fully loaded and avoid ugly tearings. 
    // For users that are on really slow connections and may be wondering what
    // is going on, we also return after a small delay (currently 500ms, which
    // is a bit longer than jQuery's default fadeOut delay).
    return new Promise(function (resolve) {
      var image = new Image();
      image.addEventListener('load', resolve.bind(null, work));
      image.addEventListener('error', resolve.bind(null, work));
      image.src = work.poster;

      setTimeout(resolve.bind(null, work), 500);
    });
  });
};

/* Load the next work from a Slot and displays it on the corresponding Card. */
Mosaic.prototype.loadCard = function (index) {
  var card = this.cards[index], slot = this.slots[index];
  var mosaic = this;

  return card.parallelLoad(this.next(index)).then(function (work) {
    // FIXME: We should display some information here about no more works being
    // available instead of keeping the loading screen forever when work is
    // undefined.
    return card.hydrate(work);
  });
};

/* Every two seconds */
var MOVEMENT_SHORTCUT_WAIT = 100;

/* Bind shortcuts to the mosaic */
Mosaic.prototype.bindGlobalShortcuts = function () {
  var mosaic = this;
  /* Move left and right on the mosaic */
  Mousetrap.bind('left', throttle(function () {
    mosaic.focusCard(mosaic.currentFocusedCard - 1);
  }, MOVEMENT_SHORTCUT_WAIT));
  Mousetrap.bind('right', throttle(function () {
    mosaic.focusCard(mosaic.currentFocusedCard + 1);
  }, MOVEMENT_SHORTCUT_WAIT));
};

/* Focus on a certain card index and add event listeners.
   Unbind the shortcuts of the old card. */
Mosaic.prototype.focusCard = function (index) {
  if (index < 0 || index >= this.cards.length) {
    return;
  }

  if (this.currentFocusedCard) {
    this.cards[this.currentFocusedCard].unbindShortcuts();
  }

  this.currentFocusedCard = index;
  this.cards[index].bindShortcuts();
  this.cards[index].focus();
};

function suggestion(mangaki_class) {
    $.post(Urls['work-detail'](mangaki_class, $('#id_work').val()), {
        'work': $('#id_work').val(),
        'problem': $('#id_problem').val(),
        'message': $('#id_message').val()
    }).success(function(data) {
        $('#alert').hide()
        if($('#success').css('display') === 'none')
            $('#success').show();
        $('#success').html('Merci d\'avoir contribué à Mangaki !');
        setTimeout(function() {
            $('#success').hide();
            $('#suggestionModal').modal('hide');
        }, 1000);
    }).error(function(data) {
        $('#success').hide();
        if($('#alert').css('display') === 'none')
            $('#alert').show();
        // for(line in data.responseJSON) {
        $('#alert').text(data.responseJSON['problem']);
        // }
    });
}
