var $entry_markdown_header = $("#entry-markdown-header");
var $entry_preview_header = $("#entry-preview-header");
var $entry_markdown = $(".entry-markdown");
var $entry_preview = $(".entry-preview");
var $page_name = $("#page-name");
var $page_message = $("#page-message");
var $upload_progress_bar = $("#progress-bar")
var $thumbnail_image = $('#preview-image')
var $image_info = $('.image-info')
var $upload_button = $('.btn-upload')
// Tabs
$entry_markdown_header.click(function(){
  $entry_markdown.addClass('active');
  $entry_preview.removeClass('active');
});

$entry_preview_header.click(function(){
  $entry_preview.addClass('active');
  $entry_markdown.removeClass('active');
});

$(document).on('shaMismatch', function() {
  bootbox.dialog({
    title: "Page has changed",
    message: "This page has changed and differs from your draft.  What do you want to do?",
    buttons: {
      ignore: {
        label: "Ignore",
        className: "btn-default",
        callback: function() {
          var info = aced.info();
          info['ignore'] = true;
          aced.info(info);
        }
      },
      discard: {
        label: "Discard Draft",
        className: "btn-danger",
        callback: function() {
          aced.discard();
        }
      },
      changes: {
        label: "Show Diff",
        className: "btn-primary",
        callback: function() {
          bootbox.alert("Draft diff not done! Sorry");
        }
      }
    }
  })
});

$(function(){
  $("#discard-draft-btn").click(function() {
    aced.discard();
  });

  $(".entry-markdown .floatingheader").click(function(){
    aced.editor.focus();
  });

  $("#delete-page-btn").click(function() {
    bootbox.confirm('Are you sure you want to delete this page?', function(result) {
      if (result) {
        deletePage();
      }
    });
  });
});

var deletePage = function() {
  var pageName = $page_name.val();
  var path = Config['RELATIVE_PATH'] + '/' + pageName;

  $.ajax({
    type: 'DELETE',
    url: path,
  }).done(function(data) {
    var msg = 'Deleted page: ' + pageName;
    bootbox.alert(msg, function() {
      location.href = '/';
    });
  }).fail(function(data, status, error) {
    bootbox.alert('Error deleting page!');
  });
};

var aced = new Aced({
  editor: $('#entry-markdown-content').find('.editor').attr('id'),
  renderer: function(md) { return MDR.convert(md) },
  info: Commit.info,
  submit: function(content) {
    var data = {
      name: $page_name.val().replace(/^\/*/g, "").replace(/\/+/g, "/"),
      message: $page_message.val(),
      content: content
    };
    // if the last char of the file name is a "/" probably the user forgot to write the file name
    var lastCharOfName = data.name.slice(-1)
    if( lastCharOfName === '/'){
      bootbox.alert("It seems that you forgot to insert the name of the file...");
    }
    else{
      // If renaming an existing page, use the old page name for the URL to PUT to
      var subPath = (PAGE_NAME) ? PAGE_NAME : data['name'];
      var path = Config['RELATIVE_PATH'] + '/' + subPath;
      var newPath = Config['RELATIVE_PATH'] + '/' + data['name'];
      var type = (Commit.info['sha']) ? "PUT" : "POST";

      $.ajax({
        type: type,
        url: path,
        data: data,
        dataType: 'json'
      }).always(function(data, status, error) {
        var res = data['responseJSON'];
        if (res && res['error']) {
          $page_name.addClass('parsley-error');
          bootbox.alert("<h3>" + res['message'] + "</h3>");
        } else {
          location.href = newPath;
        }
      });
    }

  }
});



var uploader = new plupload.Uploader({
    runtimes : 'html5',
    // button id that triggers the upload
    browse_button : 'upload-image-btn', 
    container: document.getElementById('app-wrap'),
    //end point 
    url : "/upload/",
     
    filters : {
        max_file_size : '10mb',
        mime_types: [
            {title : "Image files", extensions : "jpg,gif,png"},
        ]
    },

    unique_names : true,

    multi_selection:false,

    chunk_size : "200kb",
 
    init: {

        PostInit: function() {           
            $('#uploadfiles').click(function() {
                uploader.start();
                console.log("aaaa")
                return false;
            });
        },
 
        UploadProgress: function(up, file) {
            $(".progress-bar").css("width", (file.percent + "%") ).attr('aria-valuenow',file.percent)
        },
 
        Error: function(up, err) {
            console.log('[UploadError] :', err)
             $(".progress-bar").css("width", "100%").attr('aria-valuenow',100)
            bootbox.alert("Something went wrong during the upload")
            $('#action-buttons').fadeOut(400, function(){
              $(".progress-bar").addClass('progress-bar-failure')
              $('#response-button-failure').fadeIn()
            })
        },

        ChunkUploaded: function(up, file, info) {
            // Called when file chunk has finished uploading
            console.log('[ChunkUploaded] File:', file, "Info:", info);
        },

        FileUploaded: function(up, file, info) {
            // Called when file has finished uploading
            console.log('[FileUploaded] File:', file, "Info:", info)
            $('#action-buttons').fadeOut(400, function(){
              $(".progress-bar").addClass('progress-bar-success')
              $('#response-button-success').fadeIn()
            })
        },
    }
});
 
uploader.init();

var thumbnailEvent = function(files){
   $.each(files, function(){

    $image_info.children("#image-title").text(this.name)

    var img = new mOxie.Image();

    img.onload = function() {
      this.embed($thumbnail_image.get(0), {
        width: 60,
        height: 60,
        crop: true
      });
    };

    img.onembedded = function() {
      this.destroy();
    };

    img.onerror = function() {
      this.destroy();
    };

    img.load(this.getSource());        
        
    });
}

function resetButtons(){
    $('#response-button-failure').fadeOut()
    $('#response-button-success').fadeOut()
    $('#action-buttons').fadeIn()
    $(".progress-bar").removeClass('progress-bar-success')
    $(".progress-bar").removeClass('progress-bar-failure')
    $(".progress-bar").css("width", 0 + "%" ).attr('aria-valuenow',0)
    $thumbnail_image.html('')
}

uploader.bind('FilesAdded', function(up, files) {

   if($upload_progress_bar.css('display') !== 'none'){
       $upload_progress_bar.slideUp(400, function(){ 
        resetButtons()
        $thumbnail_image.html('')
        thumbnailEvent(files)        
        $upload_progress_bar.slideDown()
      })
   }
   else{
        resetButtons()
        thumbnailEvent(files)
        $upload_progress_bar.slideDown()
   } 
});



$(document).ready(function(){
   $('#response-button-success').hide()
   $('#response-button-failure').hide()

   $('.btn-upload-cancel').click(function() {
        $upload_progress_bar.slideUp()
   });


   $('#response-button-success .btn-upload').click(function() {
        $upload_progress_bar.slideUp()
   });

   $('#response-button-failure .btn-upload').click(function() {
        $upload_progress_bar.slideUp()
   });
})