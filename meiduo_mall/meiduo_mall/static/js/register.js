let vm = new Vue({
    el: "#app", // 通过id选择器 找到绑定的html
    //修改vue读取变量的语法
     delimiters: ['[[', ']]'],
    // 数据对象
    data:{
        //v-model
        username: '',
        password: '',
        password2: '',
        mobile: '',
        allow:'',
        //v-show,控制是否展示错误信息，默认为flase不展示
        error_name: false,
        error_password: false,
        error_password2: false,
        error_mobile: false,
        error_allow: false,

        //error_message
        error_name_message: '',
        error_mobile_message: ''

    },
    //绑定事件
    methods:{
        // 校验用户名
        check_username() {
            // 用户名是5-20个字符，[a-zA-Z0-9_-]
            // 定义正则
            let re = /^[a-zA-Z0-9_-]{5,20}$/;
            // 使用正则匹配用户名数据
            if (re.test(this.username)) {
                // 匹配成功，不展示错误提示信息
                this.error_name = false;
            } else {
                // 匹配失败，展示错误提示信息
                this.error_name_message = '请输入5-20个字符的用户名';
                this.error_name = true;
            }
        },
        // 校验密码
        check_password(){
            let re = /^[0-9A-Za-z]{8,20}$/;
            if (re.test(this.password)){
                // 密码验证通过 error_password = flase 不展示错误信息
                this.error_password = false;
            }else{
                this.error_password = true;
            }
        },
        // 校验确认密码
        check_password2() {
            if (this.password != this.password2) {
                this.error_password2 = true;
            } else {
                this.error_password2 = false;
            }
        },
         // 校验手机号
        check_mobile(){
        let re = /^1[3-9]\d{9}$/;
        if(re.test(this.mobile)) {
            this.error_mobile = false;
        } else {
            this.error_mobile_message = '您输入的手机号格式不正确';
            this.error_mobile = true;
            }
        },
        // 校验是否勾选协议
        check_allow(){
            if(!this.allow) {
            this.error_allow = true;
        } else {
            this.error_allow = false;
        }

        },
        // 监听表单提交事件
        on_submit(){
            this.check_username();
            this.check_password();
            this.check_password2();
            this.check_mobile();
            this.check_allow();

            if (this.error_name == true || this.error_password == true || this.error_password2 == true
                    || this.mobile == true || this.allow == true) {
                // 禁用掉表单的提交事件
                window.event.returnValue = false;
            }
        },
    }
});