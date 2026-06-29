class Slider {

    LOGPREFIX = "Slider: "

    events = {
        Start: "Start",
        End: "End"
    }

    classes = {
        Active: "slide-active",
        Animating: "animating",
        ListAnimating: "slider-animating",
        Horizontal: "slider-horizontal",
        Vertical: "slider-vertical"
    }

    numberSlides = 0;
    slidesPerPage = 3;
    activeIndex = 0;
    remainingMoves = 0; // Number of animations queued to be done after the current one

    contentEl = null;
    contentWidth = 0;
    isVertical = false;
    isList = false; // Whether there's a list element inside or not
    isAnimating = false; // If it's animating the clicks won't be registered
    isQueued = false; // Whether there are more animations to do after the current one
    queuedIsNext = false; // Whether the direction of the queued animation is in the "next direction" (forward)


    gap = 0.1; // Not exactly a gap per se (more like it's inverted) - the percentage of the slide's size that will be underneath the previous slide (0.1 = 10%)
    scaleDown = 0.1; // Difference in scale between a slide and the previous slide. (0.1 = every n slide after the first one is going to be (10% * n) smaller than the first one - 1st slide 100%, 2nd slide 90%, 3rd slide 80%, etc...)

    scaleArr = [1]; // Scale of the slides
    leftArr = [0]; // Left positions of the slides
    els = []; // Internal list of slides (ordered differently from the original list)
    pos = "left"; // CSS position to be used for animations
    dim = "width"; // width or height depending on the direction

    fadeInDuration = 380;
    fadeOutDuration = 350;
    fadeOutTransition = "ease-in";
    fadeInTransition = "ease-in";

    eventListener = null;

    constructor(contentId, options){
        this.init(contentId, options);
    }

    init(contentId, options) {
        this.setOptions(options);

        this.placeholderEl = document.getElementById(contentId);
        if(this.placeholderEl){
            // check if there's a list element being used
            const list = document.querySelector('#' + contentId + " > .list");
            if(list){
                this.contentEl = list;
                this.isList = true;
            }
            else {
                this.contentEl = this.placeholderEl;
            }
            this.setClickListener();
            this.initSlides();
        }
        else {
            console.error(LOGPREFIX + "Placeholder not found. Could not initialize the component");
        }
    }

    initSlides(){

        //TODO: This could use some sort of observer to see if new elements are added - Not a priority for now§

        // list-loading - Platform class used when the data hasn't been fetched yet
        if(this.isList && this.contentEl.classList.contains('list-loading')){
            setTimeout(waitList, 50);
            return;
        }
        
        this.calcVars();

    }

    // Wait for the data to be fetched
    waitList() {
        if(this.isList && this.contentEl.classList.contains('list-loading')){
            setTimeout(waitList, 50);
            return;
        }
    }

    move(isNext) {
        if(this.els.length < 2 || (this.isAnimating && !this.isQueued))
            return;
        
        this.isAnimating = true;

        this.contentEl.classList.add(this.classes.ListAnimating);

        // Index of the active slide - index of the element from the original list
        if(!isNext && this.activeIndex === 0)
            this.activeIndex = this.numberSlides - 1;
        else {
            this.activeIndex = isNext ? (this.activeIndex + 1) % this.numberSlides : this.activeIndex -1; 
        }

        this.sendEvent(this.events.Start);

        // Set the styles of the next visible slides (slide N will have the styling slide N - 1 had)
        const children = this.els;
        let startIndex = isNext ? 1 : 0; // TODO: If it's "next" the first slide is moving out so there's no point in setting that style yet maybe?
        for(let i = startIndex; i < Math.min(this.slidesPerPage + 1, this.numberSlides); i++){
            const slide = children[i];
            const nextIndex = isNext ? i - 1 : i + 1;
            slide.style.transform = "scale(" + this.scaleArr[nextIndex] + ")";
            slide.style[this.pos] = this.leftArr[nextIndex] + "px";
            slide.style.zIndex = this.numberSlides - i + (isNext ? 1 : -1);
        }

        // index of the slide that's gonna fade in (visibility related - not related to the activeIndex variable)
        const indexIn = !isNext ? this.numberSlides - 1 : (this.numberSlides > this.slidesPerPage ? this.slidesPerPage : this.numberSlides - 1);
        // new index of the slide that's gonna fade in
        const newIndexIn = isNext? indexIn : 0;

        // Slide to fade out
        const indexOut = isNext ? 0 : this.numberSlides > this.slidesPerPage ? this.slidesPerPage - 1 : this.numberSlides - 1;
        let slideOut = children[indexOut];
        slideOut.classList.add(this.classes.Animating); // using this class to cancel the default CSS transition
        slideOut.style.transform = "scale(0)";

        // Slide to fade in - if the number of slides is lower than the slides per page variable, clone the slide that's fading out (so that the fade in and out animations are simultaneous)
        // If a clone is used the clone will be replaced by the original slide after the animation (to retain the original element due to listeners and such)
        const isClone = this.numberSlides <= this.slidesPerPage;
        let slideIn = isClone ? slideOut.cloneNode(true) : children[indexIn];
        if(isClone)
            slideIn.classList.remove(this.classes.Active);

        slideOut.classList.add('hidden-slide'); // hiding the slide after the animation until it reappears
        if(!this.isVertical && isNext)
            slideOut.style.transformOrigin = "bottom left";
        slideIn.style.zIndex = isNext ? 0 : this.slidesPerPage;
        slideIn.style.display = "none";
        slideIn.style[this.pos] = this.leftArr[newIndexIn] + "px";
        //slideIn.style.transformOrigin = "0% 50%";

        const fadeOut = slideOut.animate(
            isNext ? this.nextFadeOutFrames(indexOut) : this.backFadeOutFrames(indexOut), 
            {duration: this.fadeOutDuration, iterations: 1, easing: this.fadeOutTransition})

        // Append the clone to the slider
        if(isClone)
            slideOut.parentElement.appendChild(slideIn);

        const fadeIn = slideIn.animate(
            isNext ? this.nextFadeInFrames(newIndexIn) : this.backFadeInFrames(0), 
            {duration: this.fadeInDuration, iterations: 1, easing: this.fadeInTransition})

        Promise.all([fadeOut.finished, fadeIn.finished]).then(() => {

            // Could simplify this in the future (have a single piece of code for both the clone and the new slide)
            if(isClone){
                slideOut.style.transform = "scale(" + this.scaleArr[indexIn] + ")";
                slideOut.style[this.pos] = this.leftArr[indexIn] + "px";
                slideOut.style.display = "flex";
                slideOut.classList.remove('hidden-slide');
                slideOut.classList.remove('animating');
                slideOut.style.transformOrigin = "";
            }
            else {
                //Set the styles of the new slide to match the animation's final state
                slideIn.style.transform = "scale(" + this.scaleArr[indexIn] + ")";
                slideIn.style[this.pos] = this.leftArr[indexIn] + "px";
                slideIn.style.display = "flex";
                slideIn.classList.remove('hidden-slide');
                slideIn.classList.remove('animating');
                slideIn.style.transformOrigin = "";
                slideOut.style.transformOrigin = "";
            }

            // Replace clone with original element
            if(isClone){
                slideIn.replaceWith(slideOut);
                slideIn = slideOut;
            }

            slideIn.style.zIndex = isNext ? this.numberSlides - newIndexIn : this.numberSlides;
            slideIn.style.transform = "scale(" + (isNext ? this.scaleArr[indexIn] : 1) + ")";
            //slideOut.style.transform = "scale(" + (isNext ? this.scaleArr[indexIn] : 1) + ")";

            // Rearrange internal slide array - first element becomes the last one (when its the next slide)
            if(isNext){
                const el = this.els[0];
                this.els = this.els.slice(1, this.els.length);
                this.els.push(el);
            }
            else { 
                const el = this.els[this.els.length - 1];
                this.els = this.els.slice(0, this.els.length - 1);
                this.els = [el, ...this.els];
            }

            this.contentEl.classList.remove(this.classes.ListAnimating);
            this.sendEvent(this.events.End);

            // Set the first slide as active while removing the active class from the old one
            const oldActive = this.contentEl.querySelector("." + this.classes.Active);
            if(oldActive)
                oldActive.classList.remove(this.classes.Active);
            this.els[0].classList.add(this.classes.Active);

            // Check for queued animations (when using GoTo)
            this.remainingMoves -= 1;
            if(this.remainingMoves > 0){
                setTimeout(() => {this.move(isNext)}, 1);
            }
            else {
                this.isQueued = false;
                this.isAnimating = false;
            }
        })
        
    }

    // Calculates the initial size and positions of the elements
    // Stores them all in arrays so that they aren't calculated every time (#n slide being shown will always have the same size/position)

    calcVars(){
        if(this.isVertical) {
            this.dim = "height";
            this.pos = "top";
            this.placeholderEl.classList.remove(this.classes.Horizontal);
            if(!this.placeholderEl.classList.contains(this.classes.Vertical))
                this.placeholderEl.classList.add(this.classes.Vertical);
        }
        else {
            this.dim = "width";
            this.pos = "left";
            if(!this.placeholderEl.classList.contains(this.classes.Horizontal))
                this.placeholderEl.classList.add(this.classes.Horizontal);
            this.placeholderEl.classList.remove(this.classes.Vertical);
        }
        this.contentSize = this.isVertical ? this.contentEl.getBoundingClientRect().height : this.contentEl.getBoundingClientRect().width;
        this.numberSlides = this.contentEl.childElementCount;
        let currSize = 1;
        let accumulator = 1;
        const children = this.contentEl.children;
        const firstSlide = children[0];
        this.els = Array.from(children);

        for(let i = 1; i < this.slidesPerPage; i++){
            currSize = (1 - (i * this.scaleDown));
            accumulator = accumulator + currSize - (currSize * this.gap);
            this.scaleArr.push(currSize);
        }

        let baseSize = this.contentSize / accumulator;

        // Set the styles for the first slide
        firstSlide.style.transform = "scale(1)";
        firstSlide.style[this.pos] = "0px";
        firstSlide.style[this.dim] = baseSize + "px";
        firstSlide.style.zIndex = this.numberSlides;
        firstSlide.classList.add(this.classes.Active);

        let left = baseSize;

        // Set the styles for the visible slides (except the first one)
        for(let i = 1; i < Math.min(this.slidesPerPage, this.numberSlides); i++){
            left = left - (((baseSize * this.scaleArr[i]) * this.gap));
            this.leftArr.push(left);
            //children[i].style.transformOrigin = "0% 50%";
            children[i].style[this.pos] = left + "px";
            children[i].style.transform = "scale(" + this.scaleArr[i] + ")";
            children[i].style[this.dim] = baseSize + "px";
            children[i].style.zIndex = this.numberSlides - i;
            left += (baseSize * this.scaleArr[i]);
        }

        // Set the styles for the inactive (hidden) slides
        for(let i = this.slidesPerPage; i < this.numberSlides; i++) {
            children[i].style.display = "none";
            children[i].style.zIndex = -1;
            children[i].style[this.dim] = baseSize + "px";
            children[i].style.transform = "scale(0)";
        }

        // TODO: maybe do this somewhere along the way - rearrange the for cycles
        // dataIndex = index in the original array (as in the original list fed tot he component)
        for(let i = 0; i < this.numberSlides; i++){
            children[i].dataset.dataIndex = i;
            children[i].classList.add('slide');
        }
    }

    nextFadeInFrames(index) {
        return [{
            offset: 0,
            display: "none",
            transform: "scale(0)"
        }, {
            offset: 0.01,
            display: "flex",
            transform: "scale(0)"
        },{
            offset: 1,
            display: "flex",
            transform: "scale(" + this.scaleArr[index] + ")"
        }]
    }

    backFadeInFrames(index) {
        return [{
            offset: 0,
            display: "none",
            opacity: 0,
            transform: "scale(0)"
        }, {
            offset: 0.01,
            display: "flex",
            opacity: 0,
            transform: "scale(0)"
        },{
            offset: 1,
            display: "flex",
            opacity: 1,
            transform: "scale(" + this.scaleArr[index] + ")"
        }]
    }

    nextFadeOutFrames(index) {
        return [{
            display: "flex",
            opacity: 1,
            [this.pos]: 0,
            transform: "scale(" + this.scaleArr[index] + ")"
        }, {
            display: "flex",
            opacity: 0,
            [this.pos]: 0,
            transform: "scale(0)"
        }]
    }

    backFadeOutFrames(index) {
        return [{
            display: "flex",
            transform: "scale(" + this.scaleArr[index] + ")"
        }, {
            display: "flex",
            transform: "scale(0)"
        }]
    }

    setOptions(options) {
        for (let key in options) {
            if(options.hasOwnProperty(key))
                this[key] = options[key]
        }
    }

    setClickListener() {
        if(this.moveOnClick)
            this.contentEl.addEventListener('click', () => {
                this.move(true);
            })
    }

    goTo(newIndex, isNext = undefined) {
        const currIndex = this.els[0].dataset.dataIndex;
        if(currIndex == newIndex){
            return;
        }
        // Calculate the forward distance
        const forwardDistance = (newIndex - currIndex + this.numberSlides) % this.numberSlides;
        // Calculate the backward distance
        const backwardDistance = (this.numberSlides - forwardDistance) % this.numberSlides;
        let distance, nextDirection;

        if(isNext === undefined || isNext === null){
            nextDirection = forwardDistance <= backwardDistance;
            distance = nextDirection ? forwardDistance : backwardDistance;
        }
        else if(isNext) {
            nextDirection = true;
            distance = forwardDistance;
        } else {
            nextDirection = false;
            distance = backwardDistance;
        }

        this.queuedIsNext = nextDirection;
        this.isQueued = true;
        this.remainingMoves = distance;

        this.move(nextDirection);
    }

    sendEvent(eventType) {
        this.eventListener(eventType, this.activeIndex);
    }
}