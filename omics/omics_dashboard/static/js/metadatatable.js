$(document).ready(function() {
    $('.recordtd')
        .focus(function () {
            $(this).data('initialText', $(this).html());
        })
        .blur(function() {
            if($(this).data('initialText') !== $(this).html()) {
                console.log('content changed!');
                var id_attr = $(this).attr('id').split(',');
                var collectionId = id_attr[0];
                var row = id_attr[1];
                var path = id_attr[2];
                var body = {'newValue': $(this).text()};
                var url = '/omics/api/collections/' + collectionId + '?path=' + path + '&i=' + row + '&j=0';
                console.log(url);
                $.ajax({
                    type: "PATCH",
                    data: JSON.stringify(body),
                    url: url,
                    contentType: "application/json"
                }).done(function(res){
                    console.log(res);
                    console.log(url);
                    $('#failModalLabel').text('Entry Updated');
                    console.log(res);
                    $('#failModalBody').text(res.message);
                    $('#failModal').modal();
                }).fail(function(res){
                    $('#failModalLabel').text('Update Failed');
                    console.log(url);
                    console.log(res);
                    $('#failModalBody').text(res.responseJSON.message);
                    $('#failModal').modal();
                });
            }
        });
    $('#recordMetadata').DataTable(
        {
            'scrollX': true
        }
    );
});