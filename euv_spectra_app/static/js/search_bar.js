$(".default_option").click(function(){
    $(".dropdown ul").addClass("active");
});
  
$(".dropdown ul li").click(function(){
    var text = $(this).text();
    $(".default_option").text(text);
    $(".dropdown ul").removeClass("active");

    if (text == 'Star Name'){
        $("#name-form-cont").css("display", "block");
        $("#position-form-cont").css("display", "none");
    } else if (text == 'Position') {
        $("#name-form-cont").css("display", "none");
        $("#position-form-cont").css("display", "block");
    }
});